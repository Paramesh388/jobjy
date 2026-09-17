import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    BASE_DIR = str(BASE_DIR)
    SECRET_KEY = os.environ.get("SECRET_KEY", "jobmatch_ai_super_secret_dev_key_2026")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max file size
    ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
    
    # SQLite Database
    INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
    DATABASE_PATH = os.path.join(INSTANCE_DIR, "jobmatch.db")
    
    # External Job API Configs
    ADZUNA_APP_ID = os.environ.get("ADZUNA_APP_ID", "")
    ADZUNA_APP_KEY = os.environ.get("ADZUNA_APP_KEY", "")
    JOB_API_KEY = os.environ.get("JOB_API_KEY", "")
    JOB_API_BASE_URL = os.environ.get("JOB_API_BASE_URL", "")
    FORCE_DEMO_DATA = os.environ.get("FORCE_DEMO_DATA", "False").lower() in ("true", "1", "yes")

    # ML Scoring Weights
    WEIGHT_TEXT_SIMILARITY = 0.60
    WEIGHT_SKILL_MATCH = 0.40
