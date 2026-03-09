from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from src.extenstion import db
from src.models.contact_model import ContactModel

contact_bp = Blueprint('contact', __name__)


# ── Public: Submit a contact message ─────────────────────────────────────────
@contact_bp.route('/contact', methods=['POST'])
def submit_contact():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No data provided'}), 400

    required = ['name', 'email', 'subject', 'message']
    for field in required:
        if not data.get(field, '').strip():
            return jsonify({'message': f'{field} is required'}), 422

    contact = ContactModel(
        name=data['name'].strip(),
        email=data['email'].strip(),
        subject=data['subject'].strip(),
        message=data['message'].strip(),
        inquiry_type=data.get('inquiry_type', 'general'),
    )
    db.session.add(contact)
    db.session.commit()

    return jsonify({'message': 'Your message has been received. We will get back to you soon!'}), 201


# ── Admin: List all contact messages ─────────────────────────────────────────
@contact_bp.route('/admin/contacts', methods=['GET'])
@jwt_required()
def admin_get_contacts():
    status = request.args.get('status', 'all')          # all | read | unread
    query = ContactModel.query.order_by(ContactModel.created_at.desc())

    if status == 'read':
        query = query.filter_by(is_read=True)
    elif status == 'unread':
        query = query.filter_by(is_read=False)

    contacts = query.all()
    return jsonify({
        'contacts': [c.to_dict() for c in contacts],
        'count': len(contacts),
        'unread_count': ContactModel.query.filter_by(is_read=False).count(),
    }), 200


# ── Admin: Mark message as read ───────────────────────────────────────────────
@contact_bp.route('/admin/contacts/<int:contact_id>/read', methods=['PUT'])
@jwt_required()
def admin_mark_read(contact_id):
    contact = ContactModel.query.get_or_404(contact_id)
    contact.is_read = True
    db.session.commit()
    return jsonify({'message': 'Marked as read', 'contact': contact.to_dict()}), 200


# ── Admin: Delete a contact message ──────────────────────────────────────────
@contact_bp.route('/admin/contacts/<int:contact_id>', methods=['DELETE'])
@jwt_required()
def admin_delete_contact(contact_id):
    contact = ContactModel.query.get_or_404(contact_id)
    db.session.delete(contact)
    db.session.commit()
    return jsonify({'message': 'Contact message deleted'}), 200
