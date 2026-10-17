"""User accounts. Supervisors manage everyone; users can view and edit themselves."""
from flask import Blueprint, request
from flask_login import current_user, login_required

from ..extensions import db
from ..models import User
from ..security import error, supervisor_required
from .validation import user_problem

bp = Blueprint("users", __name__)


def other_supervisors(user):
    return User.query.filter(User.role == "supervisor", User.id != user.id).count()


@bp.get("/users")
@supervisor_required
def list_users():
    return {"users": [u.to_dict() for u in User.query.order_by(User.username)]}


@bp.post("/users")
@supervisor_required
def create_user():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role") or "crew"
    phone = (data.get("phone") or "").strip() or None
    problem = user_problem(username=username, email=email, password=password, role=role, phone=phone)
    if problem:
        return error(problem, 400)
    if User.query.filter_by(username=username).first():
        return error("Username already exists", 409)
    if User.query.filter_by(email=email).first():
        return error("Email already exists", 409)
    user = User(username=username, email=email, role=role, phone=phone)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return {"user": user.to_dict()}, 201


def find_user_for(user_id):
    """The target user if the current user may manage them (self or supervisor)."""
    if current_user.id != user_id and not current_user.is_supervisor:
        return None, error("You can only manage your own account", 403)
    user = db.session.get(User, user_id)
    if not user:
        return None, error("User not found", 404)
    return user, None


@bp.get("/users/<int:user_id>")
@login_required
def get_user(user_id):
    user, problem = find_user_for(user_id)
    return problem or user.to_dict()


@bp.put("/users/<int:user_id>")
@login_required
def update_user(user_id):
    user, problem = find_user_for(user_id)
    if problem:
        return problem
    data = request.get_json(silent=True) or {}
    fields = {
        "username": (data["username"] or "").strip() if "username" in data else None,
        "email": (data["email"] or "").strip().lower() if "email" in data else None,
        "password": data.get("password") or None,
        "role": data.get("role"),
        "phone": (data.get("phone") or "").strip() if "phone" in data else None,
    }
    problem = user_problem(**fields)
    if problem:
        return error(problem, 400)
    if fields["role"] is not None and fields["role"] != user.role:
        if not current_user.is_supervisor:
            return error("Only supervisors can change roles", 403)
        if user.role == "supervisor" and not other_supervisors(user):
            return error("There must be at least one supervisor", 409)
        user.role = fields["role"]
    if fields["username"] and fields["username"] != user.username:
        if User.query.filter_by(username=fields["username"]).first():
            return error("Username already taken", 409)
        user.username = fields["username"]
    if fields["email"] and fields["email"] != user.email:
        if User.query.filter_by(email=fields["email"]).first():
            return error("Email already taken", 409)
        user.email = fields["email"]
    if fields["password"]:
        user.set_password(fields["password"])
    if fields["phone"] is not None:
        user.phone = fields["phone"] or None
    db.session.commit()
    return {"message": "User updated successfully", "user": user.to_dict()}


@bp.delete("/users/<int:user_id>")
@login_required
def delete_user(user_id):
    user, problem = find_user_for(user_id)
    if problem:
        return problem
    if user.role == "supervisor" and not other_supervisors(user):
        return error("There must be at least one supervisor", 409)
    db.session.delete(user)
    db.session.commit()
    return {"message": "User deleted successfully"}
