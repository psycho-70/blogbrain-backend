from flask import Blueprint, request, jsonify
from src.extenstion import allowed_file, UPLOAD_FOLDER
from flask_jwt_extended import jwt_required, get_jwt_identity
import os

from datetime import datetime

upload_bp = Blueprint('upload_bp', __name__)

def generate_unique_filename(filename):
    """Generate unique filename with timestamp"""
    name, ext = os.path.splitext(filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    return f"{name}_{timestamp}{ext}"

@upload_bp.route('/upload/image', methods=['POST'])
@jwt_required()
def upload_image():
    """Upload an image file"""
    try:
        if 'image' not in request.files:
            return jsonify({'message': 'No image file provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'message': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            # Generate secure unique filename
            original_filename =(file.filename)
            unique_filename = generate_unique_filename(original_filename)
            
            # Save file
            file_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            file.save(file_path)
            
            # Return file info
            return jsonify({
                'message': 'Image uploaded successfully',
                'filename': unique_filename,
                'original_filename': original_filename,
                'url': f'/uploads/{unique_filename}',
                'path': file_path
            }), 200
        else:
            return jsonify({'message': 'File type not allowed. Allowed types: png, jpg, jpeg, gif'}), 400
            
    except Exception as e:
        return jsonify({'message': f'Failed to upload image: {str(e)}'}), 500

@upload_bp.route('/uploads/<filename>', methods=['GET'])
def get_uploaded_file(filename):
    """Serve uploaded files"""
    from flask import send_from_directory
    return send_from_directory(UPLOAD_FOLDER, filename)

@upload_bp.route('/upload/delete', methods=['DELETE'])
@jwt_required()
def delete_image():
    """Delete an uploaded image"""
    try:
        data = request.get_json()
        filename = data.get('filename')
        
        if not filename:
            return jsonify({'message': 'Filename is required'}), 400
        
        # Prevent deletion of default images
        if filename == 'default.png':
            return jsonify({'message': 'Cannot delete default image'}), 400
        
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return jsonify({'message': 'Image deleted successfully'}), 200
        else:
            return jsonify({'message': 'File not found'}), 404
            
    except Exception as e:
        return jsonify({'message': f'Failed to delete image: {str(e)}'}), 500