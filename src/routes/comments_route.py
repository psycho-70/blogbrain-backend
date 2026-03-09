from flask import Blueprint, request, jsonify
from src.extenstion import db
from src.models.comment_model import CommentModel
from src.models.blog_model import BlogModel
from flask_jwt_extended import jwt_required

comments_bp = Blueprint('comments_bp', __name__)

@comments_bp.route('/blogs/<int:blog_id>/comments', methods=['POST'])
def add_comment(blog_id):
    try:
        data = request.get_json()
        if not data or not data.get('content') or not data.get('name'):
            return jsonify({'message': 'Content and Name are required'}), 400
        
        blog = BlogModel.query.get(blog_id)
        if not blog:
            return jsonify({'message': 'Blog not found'}), 404
            
        comment = CommentModel(
            content=data['content'],
            name=data['name'],
            email=data.get('email'),
            blog_id=blog_id,
            is_published=False # Default to unpublished, admin approves
        )
        
        db.session.add(comment)
        db.session.commit()
        
        return jsonify({'message': 'Comment submitted for approval', 'comment': comment.to_dict()}), 201
        
    except Exception as e:
        print(e)
        return jsonify({'message': str(e)}), 500

@comments_bp.route('/blogs/<int:blog_id>/comments', methods=['GET'])
def get_blog_comments(blog_id):
    try:
        comments = CommentModel.query.filter_by(blog_id=blog_id, is_published=True).order_by(CommentModel.created_at.desc()).all()
        return jsonify({'comments': [c.to_dict() for c in comments]}), 200
    except Exception as e:
        print(e)
        return jsonify({'message': str(e)}), 500

@comments_bp.route('/admin/comments', methods=['GET'])
@jwt_required()
def get_all_comments():
    try:
        status = request.args.get('status')
        query = CommentModel.query
        
        if status == 'pending':
            query = query.filter_by(is_published=False)
        elif status == 'published':
            query = query.filter_by(is_published=True)
            
        comments = query.order_by(CommentModel.created_at.desc()).all()
        # Enrich with blog title for admin dashboard
        result = []
        for c in comments:
            cd = c.to_dict()
            if c.blog:
                cd['blog_title'] = c.blog.title
            result.append(cd)
            
        return jsonify({'comments': result}), 200
    except Exception as e:
        print(e)
        return jsonify({'message': str(e)}), 500

@comments_bp.route('/admin/comments/<int:comment_id>/publish', methods=['PUT'])
@jwt_required()
def publish_comment(comment_id):
    try:
        comment = CommentModel.query.get(comment_id)
        if not comment:
            return jsonify({'message': 'Comment not found'}), 404
            
        comment.is_published = True
        db.session.commit()
        return jsonify({'message': 'Comment published'}), 200
    except Exception as e:
        print(e)
        return jsonify({'message': str(e)}), 500

@comments_bp.route('/admin/comments/<int:comment_id>/deny', methods=['PUT'])
@jwt_required()
def deny_comment(comment_id):
    try:
        comment = CommentModel.query.get(comment_id)
        if not comment:
            return jsonify({'message': 'Comment not found'}), 404
            
        comment.is_published = False
        db.session.commit()
        return jsonify({'message': 'Comment hidden'}), 200
    except Exception as e:
        print(e)
        return jsonify({'message': str(e)}), 500

@comments_bp.route('/admin/comments/<int:comment_id>', methods=['DELETE'])
@jwt_required()
def delete_comment(comment_id):
    try:
        comment = CommentModel.query.get(comment_id)
        if not comment:
            return jsonify({'message': 'Comment not found'}), 404
            
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'message': 'Comment deleted'}), 200
    except Exception as e:
        print(e)
        return jsonify({'message': str(e)}), 500
