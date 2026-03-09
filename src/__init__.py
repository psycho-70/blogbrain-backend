from flask import Flask, jsonify
from flask_cors import CORS
from datetime import timedelta
from src.extenstion import db, bcrypt, jwt, UPLOAD_FOLDER
from src.routes.login_route import auth_bp
from src.routes.category_route import category_bp
from src.routes.blogs_route import blog_bp
from src.routes.upload_route import upload_bp
from src.routes.chatbot_route import chatbot_bp
from src.routes.comments_route import comments_bp
from src.routes.contact_route import contact_bp
import os

def create_app():
    app = Flask(__name__)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(blog_bp, url_prefix='/api')
    app.register_blueprint(category_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(chatbot_bp, url_prefix='/api')
    app.register_blueprint(comments_bp, url_prefix='/api')
    app.register_blueprint(contact_bp, url_prefix='/api')
    # Configuration
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=7)
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

    # Initialize extensions with app
    db.init_app(app)
    bcrypt.init_app(app)
    jwt.init_app(app)
    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False,
         allow_headers=["Content-Type", "Authorization"],
         methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"])


 
  
    with app.app_context():
        db.create_all()
        # Create default admin if not exists
        from src.models.login_model import LoginModel
        LoginModel.create_default_admin()
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'message': 'Resource not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'message': 'Internal server error'}), 500
    
    # Serve uploaded files
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        from flask import send_from_directory
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    return app