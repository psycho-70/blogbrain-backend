from flask import Blueprint, request, jsonify
from src.extenstion import db
from src.models.category_model import CategoryModel
from src.models.login_model import LoginModel
from flask_jwt_extended import jwt_required, get_jwt_identity
import re

category_bp = Blueprint('category_bp', __name__)

def validate_category_data(data, is_update=False):
    """Validate category data"""
    errors = {}
    
    if not is_update and not data.get('name'):
        errors['name'] = 'Category name is required'
    elif data.get('name'):
        if len(data['name']) > 100:
            errors['name'] = 'Name cannot exceed 100 characters'
        # Check if name already exists
        existing = CategoryModel.query.filter_by(name=data['name']).first()
        if existing and (is_update and existing.id != data.get('id')):
            errors['name'] = 'Category name already exists'
    
    if data.get('description') and len(data['description']) > 500:
        errors['description'] = 'Description cannot exceed 500 characters'
    
    return errors

@category_bp.route('/categories', methods=['GET'])
def get_all_categories():
    """Get all active categories"""
    try:
        categories = CategoryModel.query.filter_by(is_active=True).all()
        return jsonify({
            'categories': [cat.to_dict() for cat in categories],
            'count': len(categories)
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch categories: {str(e)}'}), 500

@category_bp.route('/categories/<slug>', methods=['GET'])
def get_category_by_slug(slug):
    """Get category by slug"""
    try:
        category = CategoryModel.query.filter_by(slug=slug, is_active=True).first()
        if not category:
            return jsonify({'message': 'Category not found'}), 404
        
        return jsonify({
            'category': category.to_dict()
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch category: {str(e)}'}), 500

@category_bp.route('/admin/categories', methods=['GET'])
@jwt_required()
def get_admin_categories():
    """Get all categories for admin (including inactive)"""
    try:
        user_id = get_jwt_identity()
        user = LoginModel.query.get(user_id)
        if not user or user.role not in ['admin', 'author']:
            return jsonify({'message': 'Unauthorized'}), 403

        categories = CategoryModel.query.order_by(CategoryModel.name).all()
        return jsonify({
            'categories': [cat.to_dict() for cat in categories],
            'count': len(categories)
        }), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch categories: {str(e)}'}), 500

@category_bp.route('/admin/categories', methods=['POST'])
@jwt_required()
def create_category():
    """Create a new category (Admin/Author only)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        # Validate data
        errors = validate_category_data(data)
        if errors:
            return jsonify({'message': 'Validation failed', 'errors': errors}), 400
        
        # Check user permissions
        user = LoginModel.query.get(user_id)
        if not user or user.role not in ['admin', 'author']:
            return jsonify({'message': 'Unauthorized to create categories'}), 403
        
        # Create new category
        category = CategoryModel(
            name=data['name'],
            created_by=user_id,
            description=data.get('description', ''),
            image=data.get('image', '')
        )
        
        db.session.add(category)
        db.session.commit()
        
        return jsonify({
            'message': 'Category created successfully',
            'category': category.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to create category: {str(e)}'}), 500

@category_bp.route('/admin/categories/<int:category_id>', methods=['PUT'])
@jwt_required()
def update_category(category_id):
    """Update a category (Admin/Author only)"""
    try:
        user_id = get_jwt_identity()
        data = request.get_json()
        
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        
        # Find category
        category = CategoryModel.query.get(category_id)
        if not category:
            return jsonify({'message': 'Category not found'}), 404
        
        # Check permissions
        user = LoginModel.query.get(user_id)
        if not user or (user.role not in ['admin'] and category.created_by != user_id):
            return jsonify({'message': 'Unauthorized to update this category'}), 403
        
        # Validate data
        errors = validate_category_data(data, is_update=True)
        if errors:
            return jsonify({'message': 'Validation failed', 'errors': errors}), 400
        
        # Update fields
        if 'name' in data and data['name'] != category.name:
            category.name = data['name']
            category.update_slug()
        
        if 'description' in data:
            category.description = data['description']
        
        if 'image' in data:
            category.image = data['image']
        
        if 'is_active' in data and user.role == 'admin':
            category.is_active = data['is_active']
        
        db.session.commit()
        
        return jsonify({
            'message': 'Category updated successfully',
            'category': category.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to update category: {str(e)}'}), 500

@category_bp.route('/admin/categories/<int:category_id>', methods=['DELETE'])
@jwt_required()
def delete_category(category_id):
    """Delete a category (Admin only)"""
    try:
        user_id = get_jwt_identity()
        
        # Find category
        category = CategoryModel.query.get(category_id)
        if not category:
            return jsonify({'message': 'Category not found'}), 404
        
        # Check if category has blogs
        if category.blogs and len(category.blogs) > 0:
            return jsonify({
                'message': 'Cannot delete category with existing blogs',
                'blog_count': len(category.blogs)
            }), 400
        
        # Check permissions (admin only)
        user = LoginModel.query.get(user_id)
        if not user or user.role != 'admin':
            return jsonify({'message': 'Only admins can delete categories'}), 403
        
        # Delete category
        db.session.delete(category)
        db.session.commit()
        
        return jsonify({
            'message': 'Category deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Failed to delete category: {str(e)}'}), 500

@category_bp.route('/admin/categories/stats', methods=['GET'])
@jwt_required()
def get_category_stats():
    """Get category statistics"""
    try:
        user_id = get_jwt_identity()
        user = LoginModel.query.get(user_id)
        
        if not user or user.role != 'admin':
            return jsonify({'message': 'Admin access required'}), 403
        
        from src.models.blog_model import BlogModel
        from sqlalchemy import func
        
        # Get categories with blog counts
        categories = CategoryModel.query.all()
        stats = []
        
        for category in categories:
            blog_count = BlogModel.query.filter_by(category_id=category.id).count()
            stats.append({
                'category': category.to_dict(),
                'blog_count': blog_count,
                'active': category.is_active
            })
        
        # Sort by blog count descending
        stats.sort(key=lambda x: x['blog_count'], reverse=True)
        
        return jsonify({
            'stats': stats,
            'total_categories': len(categories),
            'active_categories': len([c for c in categories if c.is_active]),
            'inactive_categories': len([c for c in categories if not c.is_active])
        }), 200
        
    except Exception as e:
        return jsonify({'message': f'Failed to fetch stats: {str(e)}'}), 500