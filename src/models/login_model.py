from src.extenstion import db, bcrypt
from datetime import datetime
import os

class LoginModel(db.Model):
    __tablename__ = 'AdminUser'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(500), default='default.png')
    role = db.Column(db.String(50), default='author')  # admin, author, editor
    bio = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    blogs = db.relationship('BlogModel', back_populates='author', lazy=True, cascade='all, delete-orphan', overlaps="author_rel,blog_posts")
    categories = db.relationship('CategoryModel', back_populates='creator_rel', lazy=True, overlaps="created_categories,creator")
    
    def __init__(self, username, password, **kwargs):
        self.username = username
        self.set_password(password)
        self.name = kwargs.get('name', username.split('@')[0])
        self.profile_image = kwargs.get('profile_image', 'default.png')
        self.role = kwargs.get('role', 'author')
        self.bio = kwargs.get('bio', '')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password):
        """Check if password matches hash"""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'profile_image': self.get_profile_image_url(),
            'role': self.role,
            'bio': self.bio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
    
    def get_profile_image_url(self):
        """Get full URL for profile image"""
        if self.profile_image and self.profile_image != 'default.png':
            return f'/uploads/{self.profile_image}'
        return '/uploads/default.png'
    
    def update_profile_image(self, filename):
        """Update profile image filename"""
        # Delete old image if not default
        if self.profile_image and self.profile_image != 'default.png':
            old_path = os.path.join('uploads', self.profile_image)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        self.profile_image = filename
        self.updated_at = datetime.utcnow()
    
    @classmethod
    def create_default_admin(cls):
        """Create default admin user if it doesn't exist"""
        default_email = "admin@gmail.com"
        default_password = "123456"
        
        existing_user = cls.query.filter_by(username=default_email).first()
        if not existing_user:
            default_user = cls(
                username=default_email,
                password=default_password,
                name='Super Admin',
                role='admin',
                bio='System Administrator'
            )
            db.session.add(default_user)
            db.session.commit()
            print("Default admin user created successfully")
            return default_user
        return existing_user