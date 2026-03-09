from flask import Blueprint, request, jsonify
from src.extenstion import db
from src.models.login_model import LoginModel
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import re

auth_bp = Blueprint('auth_bp', __name__)

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def is_strong_password(password):
    """Check password strength"""
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    return True, ""

@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register():
    """Register a new user (Admin only)"""
    # Check if the current user is an admin
    current_user_id = get_jwt_identity()
    current_user = LoginModel.query.get(current_user_id)
    
    if not current_user or current_user.role != 'admin':
        return jsonify({'message': 'Unauthorized. Only admins can create new users.'}), 403

    data = request.get_json()
    
    # Validate input
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    name = data.get('name')
    profile_image = data.get('profile_image', 'default.png')
    role = data.get('role', 'author') # Default to author
    bio = data.get('bio', '')
    
    # Check required fields
    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400
    
    # Validate email format
    if not is_valid_email(username):
        return jsonify({'message': 'Invalid email format'}), 400
    
    # Check password strength
    is_strong, message = is_strong_password(password)
    if not is_strong:
        return jsonify({'message': message}), 400
    
    # Check if user already exists
    existing_user = LoginModel.query.filter_by(username=username).first()
    if existing_user:
        return jsonify({'message': 'Username already exists'}), 409
    
    try:
        # Create new user
        new_user = LoginModel(
            username=username,
            password=password,
            name=name,
            profile_image=profile_image,
            role=role,
            bio=bio
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user': new_user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Operation failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    data = request.get_json()
    
    # Validate input
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'message': 'Username and password are required'}), 400
    
    try:
        # Default admin credentials
        default_email = "admin@gmail.com"
        default_password = "123456"
        
        # Check if it's default admin login attempt
        if username == default_email and password == default_password:
            # Create default user if it doesn't exist
            user = LoginModel.create_default_admin()
            if not user:
                return jsonify({'message': 'Unable to create default user'}), 500
        else:
            # Look for existing user
            user = LoginModel.query.filter_by(username=username).first()
            
            if not user:
                return jsonify({'message': 'Invalid username or password'}), 401
            
            if not user.check_password(password):
                return jsonify({'message': 'Invalid username or password'}), 401
            
            if not user.is_active:
                return jsonify({'message': 'Account is deactivated'}), 403
        
        # Generate access token
        access_token = create_access_token(identity=str(user.id))
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'token': access_token
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Login failed: {str(e)}'}), 500

@auth_bp.route('/users', methods=['GET'])
@jwt_required()
def get_all_users():
    """Get all users (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = LoginModel.query.get(current_user_id)
        
        if not current_user or current_user.role != 'admin':
            return jsonify({'message': 'Unauthorized'}), 403
            
        users = LoginModel.query.all()
        return jsonify({
            'users': [user.to_dict() for user in users],
            'count': len(users)
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch users: {str(e)}'}), 500

@auth_bp.route('/users/<int:user_id>/toggle-status', methods=['PUT'])
@jwt_required()
def toggle_user_status(user_id):
    """Toggle user active status (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = LoginModel.query.get(current_user_id)
        
        if not current_user or current_user.role != 'admin':
            return jsonify({'message': 'Unauthorized'}), 403
            
        user = LoginModel.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        if user.id == int(current_user_id):
            return jsonify({'message': 'You cannot deactivate yourself'}), 400
            
        user.is_active = not user.is_active
        db.session.commit()
        
        return jsonify({
            'message': f"User {'activated' if user.is_active else 'deactivated'} successfully",
            'user': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@auth_bp.route('/users/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    """Delete a user (Admin only)"""
    try:
        current_user_id = get_jwt_identity()
        current_user = LoginModel.query.get(current_user_id)
        
        if not current_user or current_user.role != 'admin':
            return jsonify({'message': 'Unauthorized'}), 403
            
        user = LoginModel.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404
            
        if user.id == int(current_user_id):
            return jsonify({'message': 'You cannot delete yourself'}), 400
            
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({'message': 'User deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': str(e)}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    try:
        user_id = get_jwt_identity()
        user = LoginModel.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch profile: {str(e)}'}), 500

@auth_bp.route('/change-password', methods=['POST'])
@jwt_required()
def change_password():
    """Change user password"""
    data = request.get_json()
    
    if not data:
        return jsonify({'message': 'No data provided'}), 400
    
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    confirm_password = data.get('confirm_password')
    
    if not all([current_password, new_password, confirm_password]):
        return jsonify({'message': 'All password fields are required'}), 400
    
    if new_password != confirm_password:
        return jsonify({'message': 'New passwords do not match'}), 400
    
    is_strong, message = is_strong_password(new_password)
    if not is_strong:
        return jsonify({'message': message}), 400
    
    try:
        user_id = get_jwt_identity()
        user = LoginModel.query.get(user_id)
        
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'message': 'Current password is incorrect'}), 401
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({'message': 'Password changed successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to change password: {str(e)}'}), 500