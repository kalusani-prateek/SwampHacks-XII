from flask import Blueprint, request, jsonify, make_response
from app import db, bcrypt
from app.models import User, Site, Incident
from flask_login import login_user, logout_user, login_required, current_user

# Blueprints
auth_bp = Blueprint('auth', __name__)
user_bp = Blueprint('user', __name__)
admin_bp = Blueprint('admin', __name__)
site_bp = Blueprint('site', __name__)
incident_bp = Blueprint('incident', __name__)

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
    site_id = data.get('site_id')

    if not username or not email or not password or site_id is None:
        return make_response(jsonify({'message': 'Missing required fields (username, email, password, site_id)'}), 400)

    if User.query.filter_by(username=username).first():
        return make_response(jsonify({'message': 'Username already exists'}), 409)

    if User.query.filter_by(email=email).first():
        return make_response(jsonify({'message': 'Email already exists'}), 409)

    site = Site.query.get(site_id)
    if not site:
        return make_response(jsonify({'message': 'Site not found'}), 404)

    new_user = User(username=username, email=email, site_id=site_id)
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
    site_id = data.get('site_id')

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

    if site_id is not None:
        # Validate site exists
        site = Site.query.get(site_id)
        if not site:
            return make_response(jsonify({'message': 'Site not found'}), 404)
        user.site_id = site_id

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

# Admin site management
@admin_bp.route('/sites/<int:site_id>', methods=['DELETE'])
@login_required
def delete_site_by_admin(site_id):
    admin_check = admin_required()
    if admin_check:
        return admin_check

    site = Site.query.get(site_id)
    if not site:
        return make_response(jsonify({'message': 'Site not found'}), 404)

    db.session.delete(site)
    db.session.commit()

    return make_response(jsonify({'message': 'Site deleted'}), 200)

# Admin incident management
@admin_bp.route('/incidents/<int:incident_id>', methods=['DELETE'])
@login_required
def delete_incident_by_admin(incident_id):
    admin_check = admin_required()
    if admin_check:
        return admin_check

    incident = Incident.query.get(incident_id)
    if not incident:
        return make_response(jsonify({'message': 'Incident not found'}), 404)

    db.session.delete(incident)
    db.session.commit()

    return make_response(jsonify({'message': 'Incident deleted'}), 200)

# Site routes
@site_bp.route('/add_site', methods=['POST'])
@login_required
def create_site():
    admin_check = admin_required()
    if admin_check:
        return admin_check

    data = request.get_json()
    if not data:
        return make_response(jsonify({'message': 'No input data provided'}), 400)

    name = data.get('name')
    city = data.get('city')
    state = data.get('state')

    if not name or not city or not state:
        return make_response(jsonify({'message': 'Missing required fields'}), 400)

    if Site.query.filter_by(name=name).first():
        return make_response(jsonify({'message': 'Site name already exists'}), 409)

    new_site = Site(name=name, city=city, state=state)
    db.session.add(new_site)
    db.session.commit()

    return make_response(jsonify({
        'id': new_site.id,
        'name': new_site.name,
        'city': new_site.city,
        'state': new_site.state
    }), 201)

@site_bp.route('/get_sites', methods=['GET'])
def get_all_sites():
    sites = Site.query.all()
    return jsonify([{
        'id': site.id,
        'name': site.name,
        'city': site.city,
        'state': site.state
    } for site in sites]), 200

@site_bp.route('/<int:site_id>', methods=['PUT'])
@login_required
def update_site(site_id):
    admin_check = admin_required()
    if admin_check:
        return admin_check

    data = request.get_json()
    if not data:
        return make_response(jsonify({'message': 'No input data provided'}), 400)

    site = Site.query.get(site_id)
    if not site:
        return make_response(jsonify({'message': 'Site not found'}), 404)

    name = data.get('name')
    city = data.get('city')
    state = data.get('state')

    if name is None and city is None and state is None:
        return make_response(jsonify({'message': 'No fields to update'}), 400)

    if name is not None:
        existing_site = Site.query.filter_by(name=name).first()
        if existing_site and existing_site.id != site_id:
            return make_response(jsonify({'message': 'Site name already exists'}), 409)

    if name is not None:
        site.name = name
    if city is not None:
        site.city = city
    if state is not None:
        site.state = state

    db.session.commit()

    return make_response(jsonify({
        'id': site.id,
        'name': site.name,
        'city': site.city,
        'state': site.state
    }), 200)

# Incident routes
@incident_bp.route('/add_incident', methods=['POST'])
@login_required
def upload_incident():
    data = request.get_json()
    if not data:
        return make_response(jsonify({'message': 'No input data provided'}), 400)

    image = data.get('image')
    location = data.get('location')
    description = data.get('description')
    site_id = data.get('site_id')

    if not image or not location or not description:
        return make_response(jsonify({'message': 'Missing required fields (image, location, description)'}), 400)

    # Validate site_id if provided
    if site_id is not None:
        site = Site.query.get(site_id)
        if not site:
            return make_response(jsonify({'message': 'Site not found'}), 404)

    new_incident = Incident(
        users_username=current_user.username,
        image=image,
        location=location,
        description=description,
        site_id=site_id
    )
    db.session.add(new_incident)
    db.session.commit()

    return make_response(jsonify({
        'id': new_incident.id,
        'users_username': new_incident.users_username,
        'image': new_incident.image,
        'location': new_incident.location,
        'description': new_incident.description,
        'site_id': new_incident.site_id,
        'date_posted': new_incident.date_posted.isoformat() if new_incident.date_posted else None
    }), 201)

@incident_bp.route('/get_incidents', methods=['GET'])
def get_all_incidents():
    incidents = Incident.query.all()
    return jsonify([{
        'id': incident.id,
        'users_username': incident.users_username,
        'image': incident.image,
        'location': incident.location,
        'description': incident.description,
        'site_id': incident.site_id,
        'date_posted': incident.date_posted.isoformat() if incident.date_posted else None
    } for incident in incidents]), 200

@incident_bp.route('/<int:incident_id>', methods=['PUT'])
@login_required
def update_incident(incident_id):
    data = request.get_json()
    if not data:
        return make_response(jsonify({'message': 'No input data provided'}), 400)

    incident = Incident.query.get_or_404(incident_id)
    if incident.users_username != current_user.username:
        return make_response(jsonify({'message': 'Unauthorized to update this incident'}), 403)

    image = data.get('image')
    location = data.get('location')
    description = data.get('description')
    site_id = data.get('site_id')

    if image is not None:
        incident.image = image
    if location is not None:
        incident.location = location
    if description is not None:
        incident.description = description
    if site_id is not None:
        site = Site.query.get(site_id)
        if not site:
            return make_response(jsonify({'message': 'Site not found'}), 404)
        incident.site_id = site_id

    db.session.commit()

    return make_response(jsonify({
        'id': incident.id,
        'users_username': incident.users_username,
        'image': incident.image,
        'location': incident.location,
        'description': incident.description,
        'site_id': incident.site_id,
        'date_posted': incident.date_posted.isoformat() if incident.date_posted else None
    }), 200)

@incident_bp.route('/<int:incident_id>', methods=['DELETE'])
@login_required
def delete_incident(incident_id):
    incident = Incident.query.get_or_404(incident_id)
    if incident.users_username != current_user.username:
        return make_response(jsonify({'message': 'Unauthorized to delete this incident'}), 403)

    db.session.delete(incident)
    db.session.commit()

    return make_response(jsonify({'message': 'Incident deleted'}), 200)

# Register blueprints
# Note: In __init__.py we will register these blueprints with appropriate url_prefixes