from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id', name='fk_user_site_id'), nullable=False)  # NOT NULL

    def set_password(self, password):
        """Hash and set the password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the provided password matches the hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class Site(db.Model):
    __tablename__ = 'sites'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    city = db.Column(db.String(64), nullable=False)
    state = db.Column(db.String(64), nullable=False)
    # relationships
    users = db.relationship('User', backref='site', lazy=True)
    # incidents relationship is provided via Incident.site backref

    def __repr__(self):
        return f'<Site {self.name}>'

class Incident(db.Model):
    __tablename__ = 'incidents'
    id = db.Column(db.Integer, primary_key=True)
    users_username = db.Column(db.String(64), db.ForeignKey('users.username', name='fk_incident_user_username'), nullable=False)
    image = db.Column(db.String(256), nullable=False)  # store as string (e.g., filename or URL)
    location = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text(), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)  # added
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id', name='fk_incident_site_id'), nullable=True)
    # relationships
    user = db.relationship('User', foreign_keys=[users_username], backref='incidents')
    site = db.relationship('Site', foreign_keys=[site_id], backref='incidents')

    def __repr__(self):
        return f'<Incident {self.id}>'