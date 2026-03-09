from src.extenstion import db
from datetime import datetime

class CategoryModel(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text, default='')
    image = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('AdminUser.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    creator_rel = db.relationship('LoginModel', back_populates='categories', lazy=True, overlaps="created_categories,creator")
    posts = db.relationship('BlogModel', back_populates='category', lazy=True, overlaps="blogs")
    
    def __init__(self, name, created_by, **kwargs):
        self.name = name
        self.slug = self.generate_slug(name)
        self.created_by = created_by
        self.description = kwargs.get('description', '')
        self.image = kwargs.get('image', '')
    
    def generate_slug(self, name):
        """Generate URL-friendly slug from name"""
        import re
        from unicodedata import normalize
        
        # Normalize and lowercase
        slug = normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
        slug = slug.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug)
        slug = slug.strip('-')
        
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while CategoryModel.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def to_dict(self):
        """Convert category object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'slug': self.slug,
            'description': self.description,
            'image': f'/uploads/{self.image}' if self.image else None,
            'created_by': self.created_by,
            'creator': self.creator_rel.username if self.creator_rel else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }
    
    def update_slug(self):
        """Update slug when name changes"""
        self.slug = self.generate_slug(self.name)