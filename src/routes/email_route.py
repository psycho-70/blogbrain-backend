from flask import Blueprint, request, jsonify
from src.extenstion import db
from src.models.user_model import UserModel
from src.models.contact_model import ContactModel
from src.models.comment_model import CommentModel
from src.models.tracking_model import LeadModel
from src.models.blog_model import BlogModel
from flask_jwt_extended import jwt_required, get_jwt_identity
import resend
import os

email_bp = Blueprint('email_bp', __name__)

# Configure Resend
resend.api_key = "re_Khn2VCos_7dmGUmBk1ubUxiH1yxPUM2Pt"

@email_bp.route('/admin/email/subscribers', methods=['GET'])
@jwt_required()
def get_subscribers():
    try:
        # Aggregate emails from different sources
        subscribers = {}
        
        # 1. Users
        users = UserModel.query.all()
        for user in users:
            if user.username:
                subscribers[user.username] = user.name or user.username
        
        # 2. Contacts
        contacts = ContactModel.query.all()
        for contact in contacts:
            if contact.email:
                subscribers[contact.email] = contact.name or subscribers.get(contact.email, contact.email)
        
        # 3. Comments
        comments = CommentModel.query.all()
        for comment in comments:
            if comment.email:
                subscribers[comment.email] = comment.name or subscribers.get(comment.email, comment.email)
        
        # 4. Leads
        leads = LeadModel.query.all()
        for lead in leads:
            if lead.email:
                subscribers[lead.email] = lead.name or subscribers.get(lead.email, lead.email)
        
        # Format for response
        subscriber_list = [
            {'email': email, 'name': name}
            for email, name in subscribers.items()
        ]
        
        return jsonify(subscriber_list), 200
    except Exception as e:
        return jsonify({'message': f'Failed to fetch subscribers: {str(e)}'}), 500

@email_bp.route('/admin/email/send', methods=['POST'])
@jwt_required()
def send_custom_email():
    try:
        data = request.get_json()
        subject = data.get('subject')
        html_content = data.get('content')
        recipient_emails = data.get('recipients') # List of emails
        
        if not subject or not html_content or not recipient_emails:
            return jsonify({'message': 'Missing required fields'}), 400
            
        # Send emails
        # For simplicity and to avoid bulk sending limits on onboarding@resend.dev, 
        # we can send them in batches or one by one.
        # Resend recommends using their list features for large quantities.
        
        results = []
        for email in recipient_emails:
            try:
                r = resend.Emails.send({
                    "from": "onboarding@resend.dev", # Resend restriction for unpaid domains
                    "to": email,
                    "subject": subject,
                    "html": html_content
                })
                results.append({'email': email, 'status': 'sent'})
            except Exception as e:
                results.append({'email': email, 'status': 'failed', 'error': str(e)})
                
        return jsonify({'message': 'Email process completed', 'results': results}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to send email: {str(e)}'}), 500

@email_bp.route('/admin/email/send-newsletter', methods=['POST'])
@jwt_required()
def send_newsletter():
    try:
        data = request.get_json()
        recipient_emails = data.get('recipients')
        
        if not recipient_emails:
            return jsonify({'message': 'No recipients provided'}), 400
            
        # Get latest 3 blogs
        latest_blogs = BlogModel.query.filter_by(is_published=True).order_by(BlogModel.created_at.desc()).limit(3).all()
        
        if not latest_blogs:
            return jsonify({'message': 'No blogs found to send'}), 404
            
        # Create HTML content
        blog_items_html = ""
        for blog in latest_blogs:
            url = f"https://localhost:3000/blogs/{blog.slug}" # Example URL
            blog_items_html += f"""
                <div style="margin-bottom: 20px; border-bottom: 1px solid #eee; padding-bottom: 10px;">
                    <h3 style="margin: 0;"><a href="{url}" style="color: #8b5cf6; text-decoration: none;">{blog.title}</a></h3>
                    <p style="color: #666; font-size: 14px;">{blog.excerpt or blog.content[:150] + '...'}</p>
                </div>
            """
            
        html_template = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; border: 1px solid #ddd; padding: 20px; border-radius: 10px;">
                <h2 style="color: #8b5cf6; text-align: center;">Latest from BlogBrain</h2>
                <p>Hello! Check out our latest articles:</p>
                {blog_items_html}
                <p style="text-align: center; color: #999; font-size: 12px; margin-top: 30px;">
                    Sent by BlogBrain System. <br/>
                    aiittechjournal@gmail.com
                </p>
            </div>
        """
        
        results = []
        for email in recipient_emails:
            try:
                resend.Emails.send({
                    "from": "onboarding@resend.dev",
                    "to": email,
                    "subject": "New Articles from BlogBrain!",
                    "html": html_template
                })
                results.append({'email': email, 'status': 'sent'})
            except Exception as e:
                results.append({'email': email, 'status': 'failed', 'error': str(e)})
                
        return jsonify({'message': 'Newsletter process completed', 'results': results}), 200
    except Exception as e:
        return jsonify({'message': f'Failed to send newsletter: {str(e)}'}), 500
