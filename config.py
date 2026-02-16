import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(32).hex())
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'prose.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
    MANUSCRIPTS_DIR = os.path.join(BASE_DIR, "manuscripts")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB upload limit
