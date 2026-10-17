from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from flask_cors import CORS
from config import Config

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
migrate = Migrate()
cors = CORS()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with the app
    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)

    # Configure Flask-Login
    login_manager.login_view = 'auth.login'  # The blueprint 'auth' and view function 'login'
    login_manager.login_message_category = 'info'

    # Return JSON instead of HTML for unauthorized access
    @login_manager.unauthorized_handler
    def unauthorized():
        return jsonify({'message': 'Authentication required'}), 401

    # Register blueprints
    from app.routes import auth_bp, user_bp, admin_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(admin_bp, url_prefix='/api/admins')

    return app