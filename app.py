from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config
import logging
from logging.handlers import RotatingFileHandler
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_name=None):
    app = Flask(__name__)
    
    config_name = config_name or os.environ.get('FLASK_ENV', 'default')
    app.config.from_object(config[config_name])
    
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    from models import User
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    from routes.main import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    from routes.auth import auth as auth_blueprint
    app.register_blueprint(auth_blueprint, url_prefix='/auth')
    
    from routes.groups import groups as groups_blueprint
    app.register_blueprint(groups_blueprint)
    
    from routes.content import content as content_blueprint
    app.register_blueprint(content_blueprint)
    
    from routes.watchlist import watchlist_bp as watchlist_blueprint
    app.register_blueprint(watchlist_blueprint)
    
    from routes.ratings import ratings_bp as ratings_blueprint
    app.register_blueprint(ratings_blueprint)
    
    from routes.recommendations import recommendations_bp as recommendations_blueprint
    app.register_blueprint(recommendations_blueprint)
    
    from routes.discussions import discussion_bp as discussion_blueprint
    app.register_blueprint(discussion_blueprint)
    
    from routes.proposals import proposals_bp as proposals_blueprint
    app.register_blueprint(proposals_blueprint)
    
    # Custom Jinja2 filters
    @app.template_filter('nl2br')
    def nl2br_filter(text):
        """Convert newlines to HTML line breaks"""
        if not text:
            return text
        return text.replace('\n', '<br>')
    
    # Template context processor for CSRF token
    @app.context_processor
    def inject_csrf_token():
        from flask_wtf.csrf import generate_csrf
        return dict(csrf_token=generate_csrf)
    
    # Error handlers
    from routes.errors import errors as errors_blueprint
    app.register_blueprint(errors_blueprint)
    
    # Set up logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/watchtogether.log',
                                         maxBytes=10240, backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info('WatchTogether startup')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    return app
