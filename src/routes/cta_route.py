from flask import Blueprint, request, jsonify
from src.extenstion import db
from src.models.cta_model import CTAClickModel

cta_bp = Blueprint('cta_bp', __name__)

@cta_bp.route('/cta/click', methods=['POST'])
def click_cta():
    try:
        data = request.get_json()
        if not data or 'buttonId' not in data:
            return jsonify({'message': 'buttonId required'}), 400
            
        button_id = data['buttonId']
        
        cta = CTAClickModel.query.filter_by(button_id=button_id).first()
        if not cta:
            cta = CTAClickModel(button_id=button_id, click_count=1)
            db.session.add(cta)
        else:
            cta.click_count += 1
            
        db.session.commit()
        return jsonify({'message': 'Click incremented', 'data': cta.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Internal Server Error', 'error': str(e)}), 500

@cta_bp.route('/cta/stats', methods=['GET'])
def get_stats():
    try:
        ctas = CTAClickModel.query.all()
        return jsonify([cta.to_dict() for cta in ctas]), 200
    except Exception as e:
        return jsonify({'message': 'Internal Server Error', 'error': str(e)}), 500
