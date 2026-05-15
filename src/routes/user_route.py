from flask import Blueprint, request, jsonify
from src.extenstion import db
from src.models.user_model import UserModel
from src.models.login_model import LoginModel
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import re

user_bp = Blueprint('user_bp', __name__)

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# ── Public signup ──────────────────────────────────────────────────────────────
@user_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    name = data.get('name', '').strip()
    username = data.get('username', '').strip()   # email used as username
    password = data.get('password', '')
    confirm  = data.get('confirm_password', '')

    if not name or not username or not password:
        return jsonify({'message': 'Name, email and password are required'}), 400

    if not is_valid_email(username):
        return jsonify({'message': 'Invalid email format'}), 400

    if len(password) < 6:
        return jsonify({'message': 'Password must be at least 6 characters'}), 400

    if password != confirm:
        return jsonify({'message': 'Passwords do not match'}), 400

    # Email must not already exist in either Users or AdminUser tables
    if UserModel.query.filter_by(username=username).first():
        return jsonify({'message': 'Email already registered'}), 409
    if LoginModel.query.filter_by(username=username).first():
        return jsonify({'message': 'Email already registered'}), 409

    try:
        user = UserModel(username=username, password=password, name=name)
        db.session.add(user)
        db.session.commit()
        token = create_access_token(identity=f'user:{user.id}')
        return jsonify({
            'message': 'Account created successfully',
            'user': user.to_dict(),
            'token': token,
            'role': 'user'
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Signup failed: {str(e)}'}), 500


# ── Unified login (user + admin) ───────────────────────────────────────────────
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'message': 'Email and password are required'}), 400

    try:
        # 1. Check admin table first
        admin = LoginModel.query.filter_by(username=username).first()
        if admin:
            # Handle default admin shortcut
            if username == 'admin@gmail.com' and password == '123456':
                admin = LoginModel.create_default_admin()
            elif not admin.check_password(password):
                return jsonify({'message': 'Invalid email or password'}), 401
            if not admin.is_active:
                return jsonify({'message': 'Account is deactivated'}), 403

            token = create_access_token(identity=str(admin.id))
            return jsonify({
                'message': 'Login successful',
                'user': admin.to_dict(),
                'token': token,
                'role': admin.role   # 'admin' / 'author' / 'editor'
            }), 200

        # 2. Check public users table
        user = UserModel.query.filter_by(username=username).first()
        if user:
            if not user.check_password(password):
                return jsonify({'message': 'Invalid email or password'}), 401
            if not user.is_active:
                return jsonify({'message': 'Account is deactivated'}), 403

            token = create_access_token(identity=f'user:{user.id}')
            return jsonify({
                'message': 'Login successful',
                'user': user.to_dict(),
                'token': token,
                'role': 'user'
            }), 200

        return jsonify({'message': 'Invalid email or password'}), 401

    except Exception as e:
        return jsonify({'message': f'Login failed: {str(e)}'}), 500


# ── Get current user profile ───────────────────────────────────────────────────
@user_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    identity = get_jwt_identity()
    try:
        if str(identity).startswith('user:'):
            uid = int(identity.split(':')[1])
            user = UserModel.query.get(uid)
            if not user:
                return jsonify({'message': 'User not found'}), 404
            return jsonify({'user': user.to_dict(), 'role': 'user'}), 200
        else:
            admin = LoginModel.query.get(int(identity))
            if not admin:
                return jsonify({'message': 'User not found'}), 404
            return jsonify({'user': admin.to_dict(), 'role': admin.role}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
