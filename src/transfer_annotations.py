"""
Script para transferir anotaciones entre bases de datos de Kobo.

Uso:
    python transfer_annotations.py --source KoboReader.sqlite --target KoboReader_5ene.sqlite --dry-run
    python transfer_annotations.py --source KoboReader.sqlite --target KoboReader_5ene.sqlite
"""

import argparse
import sqlite3
import uuid
from pathlib import Path
import sys
import os

# Añadir el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from src.db_manager import SQLiteWrapper


def get_books_with_annotations(db_wrapper):
    """
    Obtiene la lista de libros que tienen anotaciones en una base de datos.
    
    Args:
        db_wrapper: SQLiteWrapper conectado a la base de datos
        
    Returns:
        DataFrame con VolumeID, Title, Author y número de anotaciones
    """
    query = """
        SELECT 
            b.VolumeID,
            c.Title,
            c.Attribution as Author,
            COUNT(*) as num_annotations
        FROM Bookmark b
        INNER JOIN content c ON b.VolumeID = c.ContentID
        WHERE b.Type IN ('highlight', 'note')
        GROUP BY b.VolumeID, c.Title, c.Attribution
        ORDER BY c.Title
    """
    return db_wrapper.get_query_df(query)


def transfer_book_annotations(db_source, db_target, volume_id_old, book_title, dry_run=True):
    """
    Transfiere las anotaciones de un libro específico entre bases de datos.
    
    Args:
        db_source: SQLiteWrapper con la BD antigua (origen)
        db_target: SQLiteWrapper con la BD nueva (destino)
        volume_id_old: VolumeID del libro en la BD antigua
        book_title: Título del libro (para búsqueda en BD nueva)
        dry_run: Si True, solo simula la transferencia
        
    Returns:
        dict con estadísticas de la transferencia
    """
    # 1. Buscar el libro en la BD nueva
    book_new = db_target.get_query_df("""
        SELECT ContentID, Title
        FROM content
        WHERE Title = ?
        AND ContentType = 6
        LIMIT 1
    """, params=(book_title,))
    
    if len(book_new) == 0:
        return {
            "status": "error",
            "message": f"Libro no encontrado en BD nueva",
            "transferred": 0,
            "skipped": 0
        }
    
    volume_id_new = book_new['ContentID'].iloc[0]
    
    # 2. Verificar si ya existen anotaciones en la BD nueva
    existing_annotations = db_target.get_query_df("""
        SELECT COUNT(*) as total
        FROM Bookmark
        WHERE VolumeID = ?
        AND Type IN ('highlight', 'note')
    """, params=(volume_id_new,))
    
    if existing_annotations['total'].iloc[0] > 0:
        return {
            "status": "skipped",
            "message": f"Ya existen {existing_annotations['total'].iloc[0]} anotaciones en BD nueva",
            "transferred": 0,
            "skipped": existing_annotations['total'].iloc[0]
        }
    
    # 3. Obtener todas las anotaciones del libro en BD antigua
    annotations_old = db_source.get_query_df("""
        SELECT *
        FROM Bookmark
        WHERE VolumeID = ?
        AND Type IN ('highlight', 'note')
    """, params=(volume_id_old,))
    
    if len(annotations_old) == 0:
        return {
            "status": "success",
            "message": "No hay anotaciones para transferir",
            "transferred": 0,
            "skipped": 0
        }
    
    # 4. Transferir las anotaciones
    stats = {
        "status": "success",
        "message": "",
        "total": len(annotations_old),
        "transferred": 0,
        "skipped": 0,
        "errors": []
    }
    
    if not dry_run:
        conn_target = db_target.connection
        cursor = conn_target.cursor()
    
    for idx, row in annotations_old.iterrows():
        try:
            # Mapear el ContentID
            old_content_id = row['ContentID']
            
            # Intentar mapear el capítulo
            if '#' in old_content_id:
                chapter_path = old_content_id.split('#')[1] if '#' in old_content_id else None
                
                if chapter_path:
                    new_content_id_query = db_target.get_query_df("""
                        SELECT ContentID
                        FROM content
                        WHERE ContentID LIKE ? || '%'
                        AND ContentID LIKE '%' || ? || '%'
                        LIMIT 1
                    """, params=(volume_id_new, chapter_path))
                    
                    if len(new_content_id_query) > 0:
                        new_content_id = new_content_id_query['ContentID'].iloc[0]
                    else:
                        new_content_id = volume_id_new
                else:
                    new_content_id = volume_id_new
            else:
                new_content_id = volume_id_new
            
            if not dry_run:
                # Insertar en la nueva BD
                cursor.execute("""
                    INSERT INTO Bookmark (
                        BookmarkID, VolumeID, ContentID, StartContainerPath,
                        StartContainerChildIndex, StartOffset, EndContainerPath,
                        EndContainerChildIndex, EndOffset, Text, Annotation,
                        ExtraAnnotationData, DateCreated, ChapterProgress,
                        Hidden, Version, DateModified, Creator, UUID, UserID,
                        SyncTime, Published, ContextString, Type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),  # Nuevo BookmarkID
                    volume_id_new,
                    new_content_id,
                    row['StartContainerPath'],
                    row['StartContainerChildIndex'],
                    row['StartOffset'],
                    row['EndContainerPath'],
                    row['EndContainerChildIndex'],
                    row['EndOffset'],
                    row['Text'],
                    row['Annotation'],
                    row['ExtraAnnotationData'],
                    row['DateCreated'],
                    row['ChapterProgress'],
                    row['Hidden'],
                    row['Version'],
                    row['DateModified'],
                    row['Creator'],
                    str(uuid.uuid4()),  # Nuevo UUID
                    row['UserID'],
                    row['SyncTime'],
                    row['Published'],
                    row['ContextString'],
                    row['Type']
                ))
            
            stats['transferred'] += 1
            
        except Exception as e:
            stats['errors'].append(f"Anotación {idx}: {str(e)}")
            stats['skipped'] += 1
    
    if not dry_run and stats['transferred'] > 0:
        conn_target.commit()
    
    return stats


def transfer_all_annotations(source_db_path, target_db_path, dry_run=True, book_filter=None):
    """
    Transfiere todas las anotaciones de una base de datos a otra.
    
    Args:
        source_db_path: Ruta a la base de datos origen
        target_db_path: Ruta a la base de datos destino
        dry_run: Si True, solo simula la transferencia
        book_filter: Lista de títulos de libros a transferir (None = todos)
        
    Returns:
        dict con estadísticas globales
    """
    print("="*80)
    print("TRANSFERENCIA MASIVA DE ANOTACIONES")
    print(f"Modo: {'SIMULACIÓN (dry_run)' if dry_run else '⚠️ EJECUCIÓN REAL'}")
    print("="*80)
    print(f"\nOrigen: {source_db_path}")
    print(f"Destino: {target_db_path}")
    
    # Conectar a las bases de datos
    db_source = SQLiteWrapper(source_db_path)
    db_source.connect()
    
    db_target = SQLiteWrapper(target_db_path)
    db_target.connect()
    
    # Obtener libros con anotaciones en BD origen
    books_source = get_books_with_annotations(db_source)
    print(f"\n📚 Libros con anotaciones en BD origen: {len(books_source)}")
    
    # Filtrar si es necesario
    if book_filter:
        books_source = books_source[books_source['Title'].isin(book_filter)]
        print(f"   Filtrados: {len(books_source)} libros")
    
    # Obtener libros con anotaciones en BD destino (para evitar duplicados)
    books_target = get_books_with_annotations(db_target)
    target_titles = set(books_target['Title'].tolist())
    print(f"📗 Libros con anotaciones en BD destino: {len(books_target)}")
    
    # Estadísticas globales
    global_stats = {
        "total_books": len(books_source),
        "processed": 0,
        "transferred": 0,
        "skipped": 0,
        "errors": 0,
        "books_success": [],
        "books_skipped": [],
        "books_error": []
    }
    
    print("\n" + "="*80)
    print("PROCESANDO LIBROS")
    print("="*80)
    
    for idx, book in books_source.iterrows():
        book_title = book['Title']
        volume_id = book['VolumeID']
        num_annotations = book['num_annotations']
        
        print(f"\n[{idx+1}/{len(books_source)}] {book_title}")
        print(f"   Autor: {book['Author']}")
        print(f"   Anotaciones: {num_annotations}")
        
        # Verificar si ya está en BD destino
        if book_title in target_titles:
            print(f"   ⏭️  OMITIDO: Ya existen anotaciones en BD destino")
            global_stats['skipped'] += num_annotations
            global_stats['books_skipped'].append(book_title)
            continue
        
        # Transferir
        result = transfer_book_annotations(
            db_source, db_target, volume_id, book_title, dry_run
        )
        
        global_stats['processed'] += 1
        
        if result['status'] == 'success':
            print(f"   ✅ TRANSFERIDO: {result['transferred']} anotaciones")
            global_stats['transferred'] += result['transferred']
            global_stats['books_success'].append(book_title)
        elif result['status'] == 'skipped':
            print(f"   ⏭️  {result['message']}")
            global_stats['skipped'] += result.get('skipped', 0)
            global_stats['books_skipped'].append(book_title)
        else:
            print(f"   ❌ ERROR: {result['message']}")
            global_stats['errors'] += 1
            global_stats['books_error'].append(book_title)
    
    # Resumen final
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    print(f"\n📊 Estadísticas:")
    print(f"   Total de libros: {global_stats['total_books']}")
    print(f"   Procesados: {global_stats['processed']}")
    print(f"   Anotaciones transferidas: {global_stats['transferred']}")
    print(f"   Anotaciones omitidas: {global_stats['skipped']}")
    print(f"   Errores: {global_stats['errors']}")
    
    if global_stats['books_success']:
        print(f"\n✅ Libros transferidos exitosamente ({len(global_stats['books_success'])}):")
        for title in global_stats['books_success'][:10]:
            print(f"   - {title}")
        if len(global_stats['books_success']) > 10:
            print(f"   ... y {len(global_stats['books_success']) - 10} más")
    
    if global_stats['books_skipped']:
        print(f"\n⏭️  Libros omitidos ({len(global_stats['books_skipped'])}):")
        for title in global_stats['books_skipped'][:5]:
            print(f"   - {title}")
        if len(global_stats['books_skipped']) > 5:
            print(f"   ... y {len(global_stats['books_skipped']) - 5} más")
    
    if global_stats['books_error']:
        print(f"\n❌ Libros con errores ({len(global_stats['books_error'])}):")
        for title in global_stats['books_error']:
            print(f"   - {title}")
    
    print("\n" + "="*80)
    
    # Cerrar conexiones
    db_source.close()
    db_target.close()
    
    return global_stats


def main():
    parser = argparse.ArgumentParser(
        description='Transferir anotaciones entre bases de datos de Kobo'
    )
    parser.add_argument(
        '--source',
        required=True,
        help='Ruta a la base de datos origen (antigua)'
    )
    parser.add_argument(
        '--target',
        required=True,
        help='Ruta a la base de datos destino (nueva)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular la transferencia sin modificar la BD destino'
    )
    parser.add_argument(
        '--books',
        nargs='+',
        help='Títulos de libros específicos a transferir (opcional)'
    )
    
    args = parser.parse_args()
    
    # Verificar que los archivos existen
    source_path = Path(args.source)
    target_path = Path(args.target)
    
    if not source_path.exists():
        print(f"❌ Error: No se encuentra la base de datos origen: {source_path}")
        sys.exit(1)
    
    if not target_path.exists():
        print(f"❌ Error: No se encuentra la base de datos destino: {target_path}")
        sys.exit(1)
    
    # Ejecutar transferencia
    stats = transfer_all_annotations(
        str(source_path),
        str(target_path),
        dry_run=args.dry_run,
        book_filter=args.books
    )
    
    # Código de salida
    if stats['errors'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
