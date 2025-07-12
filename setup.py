#!/usr/bin/env python3
"""
Setup script for WatchTogether Flask application
This script helps set up the development environment
"""

import os
import sys
import subprocess
import secrets

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def create_env_file():
    """Create .env file with secure secret key"""
    if os.path.exists('.env'):
        print("📋 .env file already exists, skipping creation")
        return True
    
    secret_key = secrets.token_urlsafe(32)
    env_content = f"""# Flask Configuration
FLASK_APP=run.py
FLASK_ENV=development
SECRET_KEY={secret_key}
DATABASE_URL=sqlite:///watchtogether.db

# Debug Mode (True for development, False for production)
DEBUG=True

# Security
WTF_CSRF_ENABLED=True
"""
    
    try:
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created .env file with secure secret key")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env file: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up WatchTogether Flask Application")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} detected")
    
    # Create virtual environment
    if not os.path.exists('venv'):
        if not run_command('python -m venv venv', 'Creating virtual environment'):
            sys.exit(1)
    else:
        print("📋 Virtual environment already exists")
    
    # Determine activation command based on OS
    if os.name == 'nt':  # Windows
        activate_cmd = 'venv\\Scripts\\activate'
        pip_cmd = 'venv\\Scripts\\pip'
        python_cmd = 'venv\\Scripts\\python'
    else:  # Unix-like systems
        activate_cmd = 'source venv/bin/activate'
        pip_cmd = 'venv/bin/pip'
        python_cmd = 'venv/bin/python'
    
    # Install requirements
    if not run_command(f'{pip_cmd} install -r requirements.txt', 'Installing Python packages'):
        sys.exit(1)
    
    # Create .env file
    if not create_env_file():
        sys.exit(1)
    
    # Initialize database
    if not run_command(f'{python_cmd} -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print(\'Database initialized\')"', 'Initializing database'):
        sys.exit(1)
    
    # Create logs directory
    if not os.path.exists('logs'):
        os.makedirs('logs')
        print("✅ Created logs directory")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print(f"1. Activate virtual environment: {activate_cmd}")
    print("2. Run the application: python run.py")
    print("3. Open your browser and go to: http://localhost:5000")
    print("\n🔐 Default admin credentials:")
    print("   Username: admin")
    print("   Password: admin123")
    print("\n⚠️  Remember to change the default credentials in production!")

if __name__ == '__main__':
    main()
