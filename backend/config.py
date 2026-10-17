import os
from datetime import timedelta

class Config:
    # Secret key for session management and JWT tokens (if used)
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-key-that-is-hard-to-guess'

    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Login configuration
    REMEMBER_COOKIE_DURATION = timedelta(days=14)
    REMEMBER_COOKIE_HTTPONLY = True
    REMEMBER_COOKIE_SECURE = False  # Set to True in production with HTTPS

    # Flask-Session configuration (if we decide to use server-side sessions)
    # SESSION_TYPE = 'filesystem'
    # SESSION_PERMANENT = False
    # SESSION_USE_SIGNER = True
    # SESSION_KEY_PREFIX = 'swamphacks:'
    # PERMANENT_SESSION_LIFETIME = timedelta(days=14)

    # Flask-CORS configuration
    CORS_HEADERS = 'Content-Type'