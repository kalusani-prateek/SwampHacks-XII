"""Flask extension instances, created here and bound to the app in create_app()."""
from flask_cors import CORS
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
cors = CORS()
