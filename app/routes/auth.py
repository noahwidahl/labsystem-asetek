from flask import Blueprint, render_template, request, redirect, url_for, jsonify, session
import os
from app.utils.entra_auth import get_current_user_entra, entra_auth
from app.utils.mssql_db import mssql_db
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login')
def login():
    """Render the Entra ID login page"""
    # Get Azure config from environment
    azure_client_id = os.environ.get('AZURE_CLIENT_ID', '')
    azure_tenant_id = os.environ.get('AZURE_TENANT_ID', '')
    
    return render_template('login.html', 
                         azure_client_id=azure_client_id, 
                         azure_tenant_id=azure_tenant_id)

@auth_bp.route('/auth/callback')
def auth_callback():
    """Handle authentication callback from Microsoft"""
    # For popup flow, we just redirect to dashboard
    # The frontend JavaScript handles the token
    return redirect(url_for('dashboard_mssql.dashboard'))

@auth_bp.route('/auth/validate', methods=['POST'])
def validate_token():
    """API endpoint to validate access token and get user info"""
    try:
        data = request.get_json()
        access_token = data.get('access_token')
        
        if not access_token:
            return jsonify({'error': 'No access token provided'}), 400
        
        # Get user info from token
        user_info = entra_auth.get_user_info_from_token(access_token)
        
        if not user_info:
            return jsonify({'error': 'Invalid access token'}), 401
        
        # Get or create user in database
        current_user = get_current_user_entra(mssql_db, access_token)
        
        # Store user info in session (optional)
        session['user_info'] = current_user
        session['access_token'] = access_token
        
        return jsonify({
            'success': True,
            'user': current_user
        })
        
    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return jsonify({'error': 'Token validation failed'}), 500

@auth_bp.route('/auth/user-info')
def get_user_info():
    """Get current user info for frontend"""
    try:
        # Get token from Authorization header
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'No valid authorization header'}), 401
        
        access_token = auth_header[7:]
        current_user = get_current_user_entra(mssql_db, access_token)
        
        if not current_user or current_user.get('UserID') == 1:  # Default admin user
            return jsonify({'error': 'User not authenticated'}), 401
        
        return jsonify({'user': current_user})
        
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        return jsonify({'error': 'Failed to get user info'}), 500

@auth_bp.route('/logout')
def logout():
    """Logout endpoint"""
    # Clear session
    session.clear()
    
    # Redirect to login with logout parameter for frontend cleanup
    return redirect(url_for('auth.login') + '?logout=true')