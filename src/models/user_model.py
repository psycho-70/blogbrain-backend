from src.extenstion import db, bcrypt
from datetime import datetime

class UserModel(db.Model):
    __tablename__ = 'Users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)  # email
    name = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    profile_image = db.Column(db.String(500), default='default.png')
    bio = db.Column(db.Text, default='')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __init__(self, username, password, name, **kwargs):
        self.username = username
        self.name = name
        self.set_password(password)
        self.bio = kwargs.get('bio', '')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'name': self.name,
            'profile_image': self.profile_image,
            'bio': self.bio,
            'is_active': self.is_active,
            'role': 'user',
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
