"""Sign-in endpoints. Sessions use Flask-Login's cookie."""
from flask import Blueprint, request
from flask_login import current_user, login_required, login_user, logout_user

from ..extensions import db
from ..models import User
from ..security import error, limiter
from .validation import user_problem

bp = Blueprint("auth", __name__)


@bp.post("/auth/register")
def register():
    """Self-registration always creates a crew account; supervisors promote people later."""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    problem = user_problem(username=username, email=email, password=password)
    if problem:
        return error(problem, 400)
    if User.query.filter_by(username=username).first():
        return error("Username already exists", 409)
    if User.query.filter_by(email=email).first():
        return error("Email already exists", 409)
    user = User(username=username, email=email, role="crew")
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return {"message": "Account created", "user": user.to_dict()}, 201


@bp.post("/auth/login")
def login():
    if not limiter.allow(f"login:{request.remote_addr}", limit=10):
        return error("Too many sign-in attempts. Wait a minute and try again.", 429)
    data = request.get_json(silent=True) or {}
    user = User.query.filter_by(username=(data.get("username") or "").strip()).first()
    if not user or not user.check_password(data.get("password") or ""):
        return error("Invalid username or password", 401)
    login_user(user, remember=True)
    return {"message": "Logged in successfully", "user": user.to_dict()}


@bp.post("/auth/logout")
@login_required
def logout():
    logout_user()
    return {"message": "Logged out successfully"}


@bp.get("/auth/me")
@login_required
def me():
    return {"user": current_user.to_dict()}
