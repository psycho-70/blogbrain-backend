from flask import Blueprint, request, jsonify
from src.extenstion import db
from src.models.tracking_model import LeadModel, UserActivityModel
from datetime import datetime

tracking_bp = Blueprint('tracking_bp', __name__)

@tracking_bp.route('/tracking/activity', methods=['POST'])
def track_activity():
    try:
        data = request.get_json()
        if not data or 'pageUrl' not in data:
            return jsonify({'message': 'pageUrl required'}), 400
            
        activity = UserActivityModel(
            visitor_id=data.get('visitorId', 'anonymous'),
            page_url=data.get('pageUrl'),
            referrer=data.get('referrer'),
            duration=data.get('duration', 0),
            user_id=data.get('userId')
        )
        db.session.add(activity)
        db.session.commit()
        return jsonify({'message': 'Activity tracked', 'id': activity.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Tracking failed', 'error': str(e)}), 500

@tracking_bp.route('/tracking/leads', methods=['POST'])
def collect_lead():
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({'message': 'Email required'}), 400
            
        # Check if lead already exists with this email for the same source
        existing = LeadModel.query.filter_by(email=data['email'], source=data.get('source')).first()
        if existing:
            # Update interests if provided
            if data.get('interests'):
                existing.interests = data['interests']
                db.session.commit()
            return jsonify({'message': 'Lead updated', 'id': existing.id}), 200
            
        lead = LeadModel(
            name=data.get('name'),
            email=data['email'],
            interests=data.get('interests'),
            source=data.get('source', 'general')
        )
        db.session.add(lead)
        db.session.commit()
        return jsonify({'message': 'Lead captured', 'id': lead.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'Lead capture failed', 'error': str(e)}), 500

@tracking_bp.route('/admin/tracking/stats', methods=['GET'])
# @jwt_required() # Add auth later if needed
def get_tracking_stats():
    try:
        leads_count = LeadModel.query.count()
        activity_count = UserActivityModel.query.count()
        recent_leads = LeadModel.query.order_by(LeadModel.created_at.desc()).limit(10).all()
        
        return jsonify({
            'totalLeads': leads_count,
            'totalActivities': activity_count,
            'recentLeads': [l.to_dict() for l in recent_leads]
        }), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch stats', 'error': str(e)}), 500

@tracking_bp.route('/admin/tracking/analytics', methods=['GET'])
def get_analytics():
    try:
        from sqlalchemy import func, desc
        from datetime import datetime, timedelta
        
        # 1. Last 14 days activity/leads
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=14)
        
        # Daily Activity
        daily_activity = db.session.query(
            func.date(UserActivityModel.timestamp).label('date'),
            func.count(UserActivityModel.id).label('count')
        ).filter(UserActivityModel.timestamp >= start_date)\
         .group_by(func.date(UserActivityModel.timestamp))\
         .all()
         
        # Daily Leads
        daily_leads = db.session.query(
            func.date(LeadModel.created_at).label('date'),
            func.count(LeadModel.id).label('count')
        ).filter(LeadModel.created_at >= start_date)\
         .group_by(func.date(LeadModel.created_at))\
         .all()
         
        # 2. Top visited pages
        top_pages = db.session.query(
            UserActivityModel.page_url,
            func.count(UserActivityModel.id).label('views')
        ).group_by(UserActivityModel.page_url)\
         .order_by(desc('views'))\
         .limit(5).all()
         
        # 3. Referrer breakdown
        referrers = db.session.query(
            UserActivityModel.referrer,
            func.count(UserActivityModel.id).label('count')
        ).group_by(UserActivityModel.referrer)\
         .order_by(desc('count'))\
         .limit(5).all()

        return jsonify({
            'dailyActivity': [{'date': str(d[0]), 'count': d[1]} for d in daily_activity],
            'dailyLeads': [{'date': str(d[0]), 'count': d[1]} for d in daily_leads],
            'topPages': [{'url': p[0], 'views': p[1]} for p in top_pages],
            'referrers': [{'name': r[0] or 'Direct', 'count': r[1]} for r in referrers]
        }), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch analytics', 'error': str(e)}), 500
