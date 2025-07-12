from app import create_app, db
from models import User, Group, GroupMember
import os

# Create Flask application
app = create_app(os.environ.get('FLASK_ENV', 'development'))

# Shell context for Flask CLI
@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'Group': Group,
        'GroupMember': GroupMember
    }

if __name__ == '__main__':
    with app.app_context():
        # Create database tables if they don't exist
        db.create_all()
        
        # Create a default user for testing (remove in production)
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', email='admin@watchtogether.com')
            admin_user.set_password('admin123')
            db.session.add(admin_user)
            db.session.commit()
            print("Created default admin user (username: admin, password: admin123)")
    
    # Run the application
    app.run(debug=app.config['DEBUG'], host='0.0.0.0', port=5000)
