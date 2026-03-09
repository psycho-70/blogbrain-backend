from flask import Blueprint, request, jsonify
from src.extenstion import db
from src.models.blog_model import BlogModel
from src.models.category_model import CategoryModel
from src.models.login_model import LoginModel
from flask_jwt_extended import jwt_required, get_jwt_identity
import urllib.request
import json
from datetime import datetime

blog_bp = Blueprint('blog_bp', __name__)

TIER_1_COUNTRIES = ['US', 'GB', 'CA', 'AU', 'NZ', 'IE', 'DE', 'FR', 'IT', 'ES', 'NL', 'SE', 'CH', 'NO', 'DK', 'FI'] # Expanded Tier 1 list, customize as needed

def is_tier_1_country(ip_addr):
    """Check if an IP belongs to a tier 1 country using iplocate.io"""
    # Allow localhost for development
    if ip_addr in ['127.0.0.1', '::1', 'localhost'] or ip_addr.startswith('192.168.'):
        return True
        
    try:
        api_key = "cf6fda5aa57bad13027337fbd47bf807"
        url = f"https://www.iplocate.io/api/lookup/{ip_addr}?apikey={api_key}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode('utf-8'))
            country_code = data.get('country_code')
            # If the API hits limit or doesn't return code, we might want to default to True or False
            if country_code and country_code in TIER_1_COUNTRIES:
                return True
            return False
    except Exception as e:
        print(f"Geolocation API error: {e}")
        # Defaulting to True on error so it doesn't break entirely if the API is down
        return True


def validate_blog_data(data, is_update=False):
    """Validate blog data"""
    errors = {}
    
    if not is_update and not data.get('title'):
        errors['title'] = 'Title is required'
    elif data.get('title') and len(data['title']) > 200:
        errors['title'] = 'Title cannot exceed 200 characters'
    
    if not is_update and not data.get('content'):
        errors['content'] = 'Content is required'
    
    if not is_update and not data.get('category_id'):
        errors['category_id'] = 'Category is required'
    elif data.get('category_id'):
        category = CategoryModel.query.get(data['category_id'])
        if not category or not category.is_active:
            errors['category_id'] = 'Invalid or inactive category'
    
    return errors

@blog_bp.route('/blogs', methods=['GET'])
def get_all_blogs():
    """Get all published blogs"""
    try:
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        else:
            client_ip = '127.0.0.1'
            
        if not is_tier_1_country(client_ip):
            return jsonify({
                'message': 'Blogs are only available in Tier 1 countries.',
                'blogs': [],
                'pagination': {'page': 1, 'per_page': 10, 'total': 0, 'pages': 0, 'has_next': False, 'has_prev': False}
            }), 403

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        per_page = min(per_page, 50)
        
        # Build query
        query = BlogModel.query.filter_by(is_published=True)
        
        # Apply filters
        category_id = request.args.get('category_id', type=int)
        if category_id:
            query = query.filter_by(category_id=category_id)
        
        author_id = request.args.get('author_id', type=int)
        if author_id:
            query = query.filter_by(author_id=author_id)
        
        featured = request.args.get('featured')
        if featured and featured.lower() == 'true':
            query = query.filter_by(is_featured=True)
        
        search = request.args.get('search')
        if search:
            query = query.filter(
                (BlogModel.title.ilike(f'%{search}%')) |
                (BlogModel.content.ilike(f'%{search}%')) |
                (BlogModel.excerpt.ilike(f'%{search}%'))
            )
        
        # Sort
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        if sort_by == 'title':
            order_field = BlogModel.title
        elif sort_by == 'views':
            order_field = BlogModel.views
        elif sort_by == 'reading_time':
            order_field = BlogModel.reading_time
        else:
            order_field = BlogModel.created_at
        
        if sort_order == 'asc':
            query = query.order_by(order_field.asc())
        else:
            query = query.order_by(order_field.desc())
        
        # Paginate
        paginated_blogs = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'blogs': [blog.to_dict() for blog in paginated_blogs.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_blogs.total,
                'pages': paginated_blogs.pages,
                'has_next': paginated_blogs.has_next,
                'has_prev': paginated_blogs.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch blogs: {str(e)}'}), 500

@blog_bp.route('/blogs/<slug>', methods=['GET'])
def get_blog_by_slug(slug):
    """Get blog by slug"""
    try:
        client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if client_ip:
            client_ip = client_ip.split(',')[0].strip()
        else:
            client_ip = '127.0.0.1'
            
        if not is_tier_1_country(client_ip):
            return jsonify({'message': 'Blogs are only available in Tier 1 countries.'}), 403

        blog = BlogModel.query.filter_by(slug=slug).first()
        
        if not blog:
            return jsonify({'message': 'Blog not found'}), 404
        
        if not blog.is_published:
            return jsonify({'message': 'This blog is not published'}), 404
        
        # Increment views
        blog.increment_views()
        
        return jsonify({
            'blog': blog.to_dict(include_content=True)
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch blog: {str(e)}'}), 500

@blog_bp.route('/admin/blogs', methods=['GET'])
@jwt_required()
def get_admin_blogs():
    """Get all blogs for admin (including unpublished)"""
    try:
        user_id = get_jwt_identity()
        user = LoginModel.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        per_page = min(per_page, 50)

        # Admin sees all blogs; author sees only their own
        query = BlogModel.query
        if user.role != 'admin':
            query = query.filter_by(author_id=user_id)

        category_id = request.args.get('category_id', type=int)
        if category_id:
            query = query.filter_by(category_id=category_id)

        status = request.args.get('status')
        if status == 'published':
            query = query.filter_by(is_published=True)
        elif status == 'draft':
            query = query.filter_by(is_published=False)

        search = request.args.get('search')
        if search:
            query = query.filter(
                (BlogModel.title.ilike(f'%{search}%')) |
                (BlogModel.content.ilike(f'%{search}%')) |
                (BlogModel.excerpt.ilike(f'%{search}%'))
            )

        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        if sort_by == 'title':
            order_field = BlogModel.title
        elif sort_by == 'views':
            order_field = BlogModel.views
        else:
            order_field = BlogModel.created_at
        if sort_order == 'asc':
            query = query.order_by(order_field.asc())
        else:
            query = query.order_by(order_field.desc())

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return jsonify({
            'blogs': [blog.to_dict() for blog in paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated.total,
                'pages': paginated.pages,
                'has_next': paginated.has_next,
                'has_prev': paginated.has_prev
            }
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch blogs: {str(e)}'}), 500

@blog_bp.route('/admin/blogs', methods=['POST'])
@jwt_required()
def create_blog():
    """Create a new blog"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        # Validate data
        errors = validate_blog_data(data)
        if errors:
            return jsonify({'message': 'Validation failed', 'errors': errors}), 400
        
        # Create blog
        blog = BlogModel(
            title=data['title'],
            content=data['content'],
            author_id=user_id,
            category_id=data['category_id'],
            excerpt=data.get('excerpt'),
            featured_image=data.get('featured_image'),
            tags=','.join(data.get('tags', [])) if isinstance(data.get('tags'), list) else data.get('tags', ''),
            meta_title=data.get('meta_title'),
            meta_description=data.get('meta_description'),
            is_published=data.get('is_published', True),
            is_featured=data.get('is_featured', False)
        )
        
        db.session.add(blog)
        db.session.commit()
        
        return jsonify({
            'message': 'Blog created successfully',
            'blog': blog.to_dict(include_content=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to create blog: {str(e)}'}), 500


@blog_bp.route('/admin/getblogs/<int:blog_id>', methods=['GET'])
@jwt_required()
def get_admin_blog(blog_id):
    """Get a single blog by id (admin/author)"""
    try:
        user_id = get_jwt_identity()
        user = LoginModel.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        blog = BlogModel.query.get(blog_id)
        if not blog:
            return jsonify({'message': 'Blog not found'}), 404

        if user.role != 'admin' and blog.author_id != user_id:
            return jsonify({'message': 'Unauthorized to view this blog'}), 403

        return jsonify({'blog': blog.to_dict(include_content=True)}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch blog: {str(e)}'}), 500

@blog_bp.route('/admin/blogs/<int:blog_id>', methods=['PUT'])
@jwt_required()
def update_blog(blog_id):
    """Update a blog"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        # Find blog
        blog = BlogModel.query.get(blog_id)
        if not blog:
            return jsonify({'message': 'Blog not found'}), 404
        
        # Check permissions
        user = LoginModel.query.get(user_id)
        if not user or (user.role not in ['admin'] and blog.author_id != user_id):
            return jsonify({'message': 'Unauthorized to update this blog'}), 403
        
        # Validate data
        errors = validate_blog_data(data, is_update=True)
        if errors:
            return jsonify({'message': 'Validation failed', 'errors': errors}), 400
        
        # Update fields
        if 'title' in data and data['title'] != blog.title:
            blog.title = data['title']
            blog.slug = blog.generate_slug(data['title'])
        
        if 'content' in data:
            blog.content = data['content']
            blog.calculate_reading_time()
        
        if 'category_id' in data:
            blog.category_id = data['category_id']
        
        if 'excerpt' in data:
            blog.excerpt = data['excerpt']
        
        if 'featured_image' in data:
            blog.featured_image = data['featured_image']
        
        if 'tags' in data:
            blog.tags = ','.join(data['tags']) if isinstance(data['tags'], list) else data['tags']
        
        if 'meta_title' in data:
            blog.meta_title = data['meta_title']
        
        if 'meta_description' in data:
            blog.meta_description = data['meta_description']
        
        if 'is_published' in data and (user.role == 'admin' or blog.author_id == user_id):
            blog.is_published = data['is_published']
        
        if 'is_featured' in data and user.role == 'admin':
            blog.is_featured = data['is_featured']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Blog updated successfully',
            'blog': blog.to_dict(include_content=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update blog: {str(e)}'}), 500

@blog_bp.route('/admin/blogs/<int:blog_id>', methods=['DELETE'])
@jwt_required()
def delete_blog(blog_id):
    """Delete a blog"""
    try:
        user_id = get_jwt_identity()
        
        # Find blog
        blog = BlogModel.query.get(blog_id)
        if not blog:
            return jsonify({'message': 'Blog not found'}), 404
        
        # Check permissions
        user = LoginModel.query.get(user_id)
        if not user or (user.role not in ['admin'] and blog.author_id != user_id):
            return jsonify({'message': 'Unauthorized to delete this blog'}), 403
        
        # Delete blog
        db.session.delete(blog)
        db.session.commit()
        
        return jsonify({
            'message': 'Blog deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to delete blog: {str(e)}'}), 500

@blog_bp.route('/admin/blogs/stats', methods=['GET'])
@jwt_required()
def get_blog_stats():
    """Get blog statistics (Global for admin, Personal for author)"""
    try:
        user_id = get_jwt_identity()
        user = LoginModel.query.get(user_id)
        if not user:
            return jsonify({'message': 'User not found'}), 404

        is_admin = user.role == 'admin'
        
        # Base queries
        blog_query = BlogModel.query
        cat_query = CategoryModel.query
        user_query = LoginModel.query
        
        if not is_admin:
            blog_query = blog_query.filter_by(author_id=user_id)
        
        # Total blogs
        total_blogs = blog_query.count()
        
        # Published blogs
        published_blogs = blog_query.filter_by(is_published=True).count()
        
        # Featured blogs
        featured_blogs = blog_query.filter_by(is_featured=True).count()
        
        # Total views
        if is_admin:
            total_views = db.session.query(db.func.sum(BlogModel.views)).scalar() or 0
            total_categories = cat_query.count()
            total_users = user_query.count()
        else:
            total_views = db.session.query(db.func.sum(BlogModel.views)).filter_by(
                author_id=user_id
            ).scalar() or 0
            total_categories = db.session.query(db.func.count(db.distinct(BlogModel.category_id))).filter_by(author_id=user_id).scalar() or 0
            total_users = 1 # Just themselves

        # Latest blogs
        latest_blogs_query = blog_query.order_by(BlogModel.created_at.desc()).limit(5).all()
        
        # Blogs per category
        from sqlalchemy import func
        if is_admin:
            category_stats = db.session.query(
                CategoryModel.name,
                func.count(BlogModel.id)
            ).join(BlogModel, isouter=True).group_by(CategoryModel.name).all()
        else:
            category_stats = db.session.query(
                CategoryModel.name,
                func.count(BlogModel.id)
            ).join(BlogModel).filter(
                BlogModel.author_id == user_id
            ).group_by(CategoryModel.name).all()
        
        return jsonify({
            'stats': {
                'total_blogs': total_blogs,
                'total_categories': total_categories if is_admin else total_categories,
                'total_users': total_users if is_admin else 1,
                'total_views': total_views,
                'published_blogs': published_blogs,
                'draft_blogs': total_blogs - published_blogs,
                'featured_blogs': featured_blogs,
                'average_views': round(total_views / total_blogs, 2) if total_blogs > 0 else 0
            },
            'category_distribution': [
                {'category': cat[0], 'count': cat[1]} for cat in category_stats
            ],
            'latest_blogs': [blog.to_dict() for blog in latest_blogs_query]
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch stats: {str(e)}'}), 500