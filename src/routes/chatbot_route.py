"""API routes for Einsteine chatbot and Admin blog generator."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from src.services.blog_generator import BlogGeneratorService
from src.services.einsteine_agent import EinsteineAgentService

chatbot_bp = Blueprint('chatbot_bp', __name__)
blog_generator = BlogGeneratorService()
einsteine_agent = EinsteineAgentService()


# --- Public: Einsteine Website Agent ---

@chatbot_bp.route('/chat/einsteine', methods=['POST'])
def einsteine_chat():
    """
    Chat with Einsteine™ - the main website AI agent.
    No auth required - for all visitors.
    """
    try:
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        chat_history = data.get('chat_history', [])
        entry_source = data.get('entry_source')  # e.g. "google", "ads", "social"
        landing_context = data.get('landing_context')  # e.g. "AI article", "Beauty content"
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
        
        response = einsteine_agent.chat(
            user_message=message,
            chat_history=chat_history,
            entry_source=entry_source,
            landing_context=landing_context,
        )
        
        return jsonify({
            'response': response,
            'success': True,
        }), 200
        
    except ValueError as e:
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        return jsonify({
            'error': 'Failed to get response from Einsteine',
            'detail': str(e),
        }), 500


# --- Admin: Blog Generator (JWT required) ---

@chatbot_bp.route('/chat/blog-generator', methods=['POST'])
@jwt_required()
def blog_generator_chat():
    """
    Chat with the admin blog generator AI.
    Helps create drafts, titles, excerpts, FAQs, SEO content.
    Can also generate structured JSON for auto-filling fields.
    """
    try:
        data = request.get_json() or {}
        message = data.get('message', '').strip()
        chat_history = data.get('chat_history', [])
        category_hint = data.get('category_hint')
        level_hint = data.get('level_hint')
        
        if not message:
            return jsonify({'error': 'Message is required'}), 400
            
        # New: support for structured generation
        if data.get('generate_json'):
            print(f"DEBUG: Generating JSON for topic: {message}")
            try:
                result = blog_generator.generate_json(
                    topic=message,
                    category=category_hint,
                    level=level_hint
                )
                return jsonify({
                    'blog': result,
                    'success': True,
                }), 200
            except Exception as e:
                print(f"ERROR in generate_json: {str(e)}")
                return jsonify({
                    'error': 'Internal Service Error during generation',
                    'detail': str(e),
                    'success': False
                }), 500

        response = blog_generator.generate(
            user_input=message,
            chat_history=chat_history,
            category_hint=category_hint,
            level_hint=level_hint,
        )
        
        return jsonify({
            'response': response,
            'success': True,
        }), 200
        
    except Exception as e:
        import traceback
        print(f"ERROR in blog_generator_chat: {str(e)}")
        traceback.print_exc()
        return jsonify({
            'error': 'Failed to process request',
            'detail': str(e),
            'success': False
        }), 500
