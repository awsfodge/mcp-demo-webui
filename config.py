"""
Configuration for MCP Demo Standalone Application
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration for MCP Demo"""
    
    # Flask configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'mcp-demo-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = Path('./flask_session')
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # WebSocket configuration
    SOCKETIO_ASYNC_MODE = 'threading'
    SOCKETIO_CORS_ALLOWED_ORIGINS = "*"
    
    # MCP Configuration
    MCP_CONFIG_PATH = Path('./data/mcp_servers.json')
    MCP_CONNECTION_TIMEOUT = float(os.getenv('MCP_CONNECTION_TIMEOUT', '30.0'))
    MCP_TOOL_TIMEOUT = float(os.getenv('MCP_TOOL_TIMEOUT', '60.0'))
    
    # AWS Configuration for Bedrock
    AWS_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
    AWS_PROFILE = os.getenv('AWS_PROFILE', None)
    
    # Model Configuration
    DEFAULT_MODEL_ID = os.getenv('DEFAULT_MODEL_ID', 'amazon.nova-lite-v1:0')
    DEFAULT_TEMPERATURE = float(os.getenv('DEFAULT_TEMPERATURE', '0.7'))
    DEFAULT_MAX_TOKENS = int(os.getenv('DEFAULT_MAX_TOKENS', '9500'))
    
    # Default System Prompt
    DEFAULT_SYSTEM_PROMPT = os.getenv(
        'DEFAULT_SYSTEM_PROMPT',
        'You are a helpful AI assistant with access to MCP tools.'
    )
    
    @classmethod
    def init_app(cls, app):
        """Initialize application with configuration"""
        # Create necessary directories
        cls.SESSION_FILE_DIR.mkdir(exist_ok=True)
        Path('./data').mkdir(exist_ok=True)
        Path('./logs').mkdir(exist_ok=True)
        
        # Set Flask configuration
        for key in dir(cls):
            if key.isupper() and not key.startswith('_'):
                app.config[key] = getattr(cls, key)
        
        # Ensure MCP config file exists
        if not cls.MCP_CONFIG_PATH.exists():
            # Create default configuration
            import json
            default_config = {
                "active_servers": {},
                "settings": {
                    "auto_reconnect": True,
                    "connection_timeout": 30.0,
                    "tool_timeout": 60.0,
                    "session_init_timeout": 15.0,
                    "list_tools_timeout": 10.0,
                    "max_concurrent_tools": 5,
                    "log_tool_calls": True
                }
            }
            cls.MCP_CONFIG_PATH.parent.mkdir(exist_ok=True)
            with open(cls.MCP_CONFIG_PATH, 'w') as f:
                json.dump(default_config, f, indent=2)

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    # Use environment variable for secret key in production
    SECRET_KEY = os.getenv('SECRET_KEY')
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable must be set in production")

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])