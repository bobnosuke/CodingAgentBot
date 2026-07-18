"""
Configuration management for CoderAgent
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    
    # Discord
    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
    BOT_OWNER_ID = os.getenv("OWNER_ID")
    
    # OpenRouter API
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./coderagent.db")
    
    # Encryption
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
    
    # Paths
    BASE_DIR = Path(__file__).parent
    STORAGE_DIR = BASE_DIR / "storage"
    LOGS_DIR = BASE_DIR / "logs"
    
    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE = LOGS_DIR / "coderagent.log"
    
    # Session Configuration
    SESSION_TIMEOUT_HOURS = 24
    SESSION_CACHE_CLEANUP_DAYS = 3
    
    # File Configuration
    MAX_FILE_SIZE_MB = 25  # Discord's file size limit
    MAX_FILES_PER_SESSION = 50
    
    CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")

    # AI Configuration
    DEFAULT_AI_MODEL = "openrouter/auto"
    AI_TIMEOUT_SECONDS = 120
    
    @classmethod
    def validate(cls) -> bool:
        """Validate required configuration"""
        required = ["DISCORD_TOKEN", "OPENROUTER_API_KEY"]
        # If GEMINI_API_KEY is not set, CEREBRAS_API_KEY is required for requirement definition
        if not cls.GEMINI_API_KEY:
            required.append("CEREBRAS_API_KEY")
        missing = [key for key in required if not getattr(cls, key)]
        
        if missing:
            print(f"❌ 必須の設定が不足しています: {", ".join(missing)}")
            return False
        
        # Create necessary directories
        cls.STORAGE_DIR.mkdir(exist_ok=True)
        cls.LOGS_DIR.mkdir(exist_ok=True)
        
        print("✅ 設定が正常に検証されました")
        return True
        
print("Cerebras Key:", bool(Config.CEREBRAS_API_KEY))
