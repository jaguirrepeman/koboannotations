import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Notion Configuration
NOTION_API_TOKEN = os.getenv('NOTION_API_TOKEN')
NOTION_BOOKS_DATABASE_ID = os.getenv('NOTION_BOOKS_DATABASE_ID')
NOTION_ANNOTATIONS_DATABASE_ID = os.getenv('NOTION_ANNOTATIONS_DATABASE_ID')

# Dropbox Configuration
APP_KEY = os.getenv('APP_KEY')
APP_SECRET = os.getenv('APP_SECRET')

# SQLite Database Configuration
SQLITE_PATH = os.getenv('SQLITE_PATH', 'KoboReader.sqlite')

# Token file for Dropbox authentication
TOKEN_FILE = 'dropbox_token.json'