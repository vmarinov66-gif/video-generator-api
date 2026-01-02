# config.py
"""
Configuration settings for Video Generator API
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration"""
    
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    
    # CORS Settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    
    # Base directories
    BASE_DIR = Path(__file__).parent
    UPLOAD_FOLDER = BASE_DIR / 'uploads'
    OUTPUT_FOLDER = BASE_DIR / 'outputs'
    MUSIC_LIBRARY_PATH = BASE_DIR / 'music_library'
    
    # Create directories if they don't exist
    UPLOAD_FOLDER.mkdir(exist_ok=True)
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    MUSIC_LIBRARY_PATH.mkdir(exist_ok=True)
    
    # File upload settings
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 10))
    MAX_TOTAL_SIZE_MB = int(os.getenv('MAX_TOTAL_SIZE_MB', 100))
    ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'bmp'}
    ALLOWED_AUDIO_EXTENSIONS = {'mp3', 'wav', 'm4a'}
    
    # Video generation settings
    MAX_CONCURRENT_VIDEOS = int(os.getenv('MAX_CONCURRENT_VIDEOS', 3))
    
    # File retention (in hours)
    UPLOAD_RETENTION_HOURS = int(os.getenv('UPLOAD_RETENTION_HOURS', 24))
    OUTPUT_RETENTION_HOURS = int(os.getenv('OUTPUT_RETENTION_HOURS', 48))
    
    # Video quality presets
    VIDEO_QUALITY_PRESETS = {
        'low': {
            'resolution': (1280, 720),
            'bitrate': '500k',
            'audio_bitrate': '96k',
            'fps': 30,
            'preset': 'ultrafast'
        },
        'medium': {
            'resolution': (1280, 720),
            'bitrate': '1500k',
            'audio_bitrate': '128k',
            'fps': 30,
            'preset': 'medium'
        },
        'high': {
            'resolution': (1920, 1080),
            'bitrate': '3000k',
            'audio_bitrate': '192k',
            'fps': 30,
            'preset': 'slow'
        }
    }
    
    @staticmethod
    def init_app(app):
        """Initialize application with config"""
        pass


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    FLASK_ENV = 'testing'


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}