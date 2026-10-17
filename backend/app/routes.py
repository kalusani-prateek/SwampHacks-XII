from flask import Blueprint, request, jsonify, make_response
from app import db, bcrypt
from app.models import User
from flask_login import login_user, logout_user, login_required, current_user

# Blueprints
auth_bp = Blueprint('auth', __name__)
user_bp = Blueprint('user', __name__)
admin_bp = Blueprint('admin', __name__)

# Helper function to check if user is admin
def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        return make_response(jsonify({'message': 'Admin privileges required!'}), 403)
    return None

# Auth routes
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return make_response(jsonify({'message': 'No input data provided'}), 400)

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return make_response(jsonify({'message': 'Missing required fields'}), 400)

    if User.query.filter_by(username=username).first():
        return make_response(jsonify({'message': 'Username already exists'}), 409)

    if User.query.filter_by(email=email).first():
        return make_response(jsonify({'message': 'Email already exists'}), 409)

    new_user = User(username=username, email=email)
    new_user.set_password(password)

    db.session.add(new_user)
    db.session.commit()

    return make_response(jsonify({'message': 'User created successfully'}), 201)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return make_response(jsonify({'message': 'No input data provided'}), 400)

    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return make_response(jsonify({'message': 'Missing username or password'}), 400)

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        return make_response(jsonify({'message': 'Logged in successfully'}), 200)
    else:
        return make_response(jsonify({'message': 'Invalid username or password'}), 401)

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return make_response(jsonify({'message': 'Logged out successfully'}), 200)

# User routes
@user_bp.route('/<int:user_id>', methods=['GET'])
@login_required
def get_user(user_id):
    # Users can only get their own data unless they are admin
    if current_user.id != user_id and not current_user.is_admin:
        return make_response(jsonify({'message': 'Unauthorized access'}), 403)

    user = User.query.get(user_id)
    if not user:
        return make_response(jsonify({'message': 'User not found'}), 404)

    return make_response(jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_admin': user.is_admin
    }), 200)

@user_bp.route('/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    # Users can only update their own data unless they are admin
    if current_user.id != user_id and not current_user.is_admin:
        return make_response(jsonify({'message': 'Unauthorized access'}), 403)

    user = User.query.get(user_id)
    if not user:
        return make_response(jsonify({'message': 'User not found'}), 404)

    data = request.get_json()
    if not data:
        return make_response(jsonify({'message': 'No input data provided'}), 400)

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if username:
        # Check if username is taken by another user
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user_id:
            return make_response(jsonify({'message': 'Username already taken'}), 409)
        user.username = username

    if email:
        # Check if email is taken by another user
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user_id:
            return make_response(jsonify({'message': 'Email already taken'}), 409)
        user.email = email

    if password:
        user.set_password(password)

    db.session.commit()

    return make_response(jsonify({'message': 'User updated successfully'}), 200)

@user_bp.route('/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    # Only admin can delete users (or users can delete themselves? We'll allow self-delete and admin delete)
    if current_user.id != user_id and not current_user.is_admin:
        return make_response(jsonify({'message': 'Unauthorized access'}), 403)

    user = User.query.get(user_id)
    if not user:
        return make_response(jsonify({'message': 'User not found'}), 404)

    db.session.delete(user)
    db.session.commit()

    return make_response(jsonify({'message': 'User deleted successfully'}), 200)

# Admin routes
@admin_bp.route('/users', methods=['GET'])
@login_required
def get_all_users():
    admin_check = admin_required()
    if admin_check:
        return admin_check

    users = User.query.all()
    user_list = []
    for user in users:
        user_list.append({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_admin': user.is_admin
        })

    return make_response(jsonify({'users': user_list}), 200)

@admin_bp.route('/users/<int:user_id>', methods=['GET'])
@login_required
def get_user_by_admin(user_id):
    admin_check = admin_required()
    if admin_check:
        return admin_check

    user = User.query.get(user_id)
    if not user:
        return make_response(jsonify({'message': 'User not found'}), 404)

    return make_response(jsonify({
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'is_admin': user.is_admin
    }), 200)

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user_by_admin(user_id):
    admin_check = admin_required()
    if admin_check:
        return admin_check

    user = User.query.get(user_id)
    if not user:
        return make_response(jsonify({'message': 'User not found'}), 404)

    data = request.get_json()
    if not data:
        return make_response(jsonify({'message': 'No input data provided'}), 400)

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    is_admin = data.get('is_admin')

    if username:
        existing_user = User.query.filter_by(username=username).first()
        if existing_user and existing_user.id != user_id:
            return make_response(jsonify({'message': 'Username already taken'}), 409)
        user.username = username

    if email:
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and existing_user.id != user_id:
            return make_response(jsonify({'message': 'Email already taken'}), 409)
        user.email = email

    if password:
        user.set_password(password)

    if is_admin is not None:
        user.is_admin = bool(is_admin)

    db.session.commit()

    return make_response(jsonify({'message': 'User updated successfully'}), 200)

@admin_bp.route('/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user_by_admin(user_id):
    admin_check = admin_required()
    if admin_check:
        return admin_check

    user = User.query.get(user_id)
    if not user:
        return make_response(jsonify({'message': 'User not found'}), 404)

    db.session.delete(user)
    db.session.commit()

    return make_response(jsonify({'message': 'User deleted successfully'}), 200)