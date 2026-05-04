from src.extenstion import db
from datetime import datetime

import os

class BlogModel(db.Model):
    __tablename__ = 'blogs'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(255), unique=True, nullable=False)
    content = db.Column(db.Text, nullable=False)
    excerpt = db.Column(db.String(300))
    featured_image = db.Column(db.String(500))
    author_id = db.Column(db.Integer, db.ForeignKey('AdminUser.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    tags = db.Column(db.String(500))
    meta_title = db.Column(db.String(200))
    meta_description = db.Column(db.String(300))
    is_published = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    views = db.Column(db.Integer, default=0)
    reading_time = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = db.relationship('LoginModel', back_populates='blogs', lazy=True, overlaps="author_rel,blog_posts")
    category = db.relationship('CategoryModel', back_populates='posts', lazy=True, overlaps="blogs")
    comments = db.relationship('CommentModel', back_populates='blog', cascade='all, delete-orphan')
    
    def __init__(self, title, content, author_id, category_id, **kwargs):
        self.title = title
        self.slug = self.generate_slug(title)
        self.content = content
        self.author_id = author_id
        self.category_id = category_id
        self.excerpt = kwargs.get('excerpt', content[:200] + '...' if len(content) > 200 else content)
        self.featured_image = kwargs.get('featured_image', '')
        self.tags = kwargs.get('tags', '')
        self.meta_title = kwargs.get('meta_title', title)
        self.meta_description = kwargs.get('meta_description', content[:150] + '...' if len(content) > 150 else content)
        self.is_published = kwargs.get('is_published', True)
        self.is_featured = kwargs.get('is_featured', False)
        self.calculate_reading_time()
    
    def generate_slug(self, title):
        """Generate URL-friendly slug from title"""
        import re
        from unicodedata import normalize
        
        slug = normalize('NFKD', title).encode('ascii', 'ignore').decode('ascii')
        slug = slug.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'[\s-]+', '-', slug)
        slug = slug.strip('-')
        
        # Ensure uniqueness
        base_slug = slug
        counter = 1
        while BlogModel.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        return slug
    
    def calculate_reading_time(self):
        """Calculate reading time based on word count"""
        word_count = len(self.content.split())
        reading_time = max(1, round(word_count / 200))
        self.reading_time = reading_time
    
    def to_dict(self, include_content=False):
        """Convert blog object to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'content': self.content if include_content else None,
            'excerpt': self.excerpt,
            'featured_image': f'/uploads/{os.path.basename(self.featured_image)}' if self.featured_image else None,
            'author': {
                'id': self.author_id,
                'username': self.author.username if self.author else None,
                'profile_image': self.author.get_profile_image_url() if self.author else None
            },
            'category': {
                'id': self.category_id,
                'name': self.category.name if self.category else None,
                'slug': self.category.slug if self.category else None
            } if self.category else None,
            'tags': self.tags.split(',') if self.tags else [],
            'meta_title': self.meta_title,
            'meta_description': self.meta_description,
            'is_published': self.is_published,
            'is_featured': self.is_featured,
            'views': self.views,
            'reading_time': self.reading_time,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def increment_views(self):
        """Increment view count"""
        self.views += 1
        db.session.commit()