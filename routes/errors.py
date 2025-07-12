from flask import Blueprint, render_template

errors = Blueprint('errors', __name__)

@errors.app_errorhandler(404)
def not_found_error(error):
    """404 error handler"""
    return render_template('errors/404.html'), 404

@errors.app_errorhandler(500)
def internal_error(error):
    """500 error handler"""
    return render_template('errors/500.html'), 500

@errors.app_errorhandler(403)
def forbidden_error(error):
    """403 error handler"""
    return render_template('errors/403.html'), 403
