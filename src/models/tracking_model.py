from src.extenstion import db
from datetime import datetime

class LeadModel(db.Model):
    __tablename__ = 'leads'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=True)
    email = db.Column(db.String(255), nullable=False)
    interests = db.Column(db.Text, nullable=True)  # Comma separated or JSON
    source = db.Column(db.String(100), nullable=True)  # e.g., "chatbot", "contact_form", "footer_newsletter"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'interests': self.interests,
            'source': self.source,
            'createdAt': self.created_at.isoformat() if self.created_at else None
        }

class UserActivityModel(db.Model):
    __tablename__ = 'user_activity'
    
    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(255), nullable=False)  # Anonymous UUID
    page_url = db.Column(db.String(500), nullable=False)
    referrer = db.Column(db.String(500), nullable=True)
    duration = db.Column(db.Integer, default=0)  # Seconds spent on page
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=True)  # If logged in
    
    def to_dict(self):
        return {
            'id': self.id,
            'visitorId': self.visitor_id,
            'pageUrl': self.page_url,
            'referrer': self.referrer,
            'duration': self.duration,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'userId': self.user_id
        }
