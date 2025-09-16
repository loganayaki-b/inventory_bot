# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from project root .env
BASE_DIR = Path(__file__).parent.parent.parent
load_dotenv(BASE_DIR / ".env")

class Settings:
    # Project paths
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "backend" / "data"
    INVENTORY_DATA_PATH = DATA_DIR / "inventory_data.xlsx"
    
    # API settings
    API_HOST = os.getenv("API_HOST", "127.0.0.1")
    API_PORT = int(os.getenv("API_PORT", "8000"))
    
    # Gemini AI settings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.0-flash-exp")

    # Email settings
    EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
    EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
    EMAIL_FROM = os.getenv("EMAIL_FROM", "")
    
    # Application settings
    DEBUG = os.getenv("DEBUG", "true").lower() == "true"
    APP_NAME = os.getenv("APP_NAME", "Inventory Forecasting System")
    
settings = Settings()