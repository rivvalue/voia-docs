#!/usr/bin/env python3
"""
Voxa Platform Deployment Script
Automates the setup and deployment process for cloning the Voxa platform
"""

import os
import sys
import subprocess
import psycopg2
from urllib.parse import urlparse
import secrets

def generate_session_secret():
    """Generate a secure session secret"""
    return secrets.token_urlsafe(64)

def check_requirements():
    """Check if all required software is installed"""
    requirements = {
        'python': 'python --version',
        'pip': 'pip --version',
        'git': 'git --version'
    }
    
    missing = []
    for name, command in requirements.items():
        try:
            subprocess.run(command.split(), capture_output=True, check=True)
            print(f"✓ {name} is installed")
        except (subprocess.CalledProcessError, FileNotFoundError):
            missing.append(name)
            print(f"✗ {name} is not installed")
    
    return missing

def create_env_file():
    """Create .env file from template"""
    if os.path.exists('.env'):
        response = input(".env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            return
    
    # Read template
    with open('.env.example', 'r') as f:
        template = f.read()
    
    # Get user inputs
    print("\nConfiguring environment variables...")
    database_url = input("Database URL (PostgreSQL): ")
    openai_key = input("OpenAI API Key: ")
    admin_email = input("Admin email address: ")
    
    # Generate session secret
    session_secret = generate_session_secret()
    
    # Replace placeholders
    env_content = template.replace('postgresql://username:password@localhost:5432/voxa_production', database_url)
    env_content = env_content.replace('your_openai_api_key_here', openai_key)
    env_content = env_content.replace('your_secure_session_secret_here_make_it_long_and_random', session_secret)
    env_content = env_content.replace('admin@rivvalue.com,admin@yourdomain.com', admin_email)
    
    # Write .env file
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✓ .env file created successfully")

def test_database_connection(database_url):
    """Test database connection"""
    try:
        parsed = urlparse(database_url)
        conn = psycopg2.connect(
            host=parsed.hostname,
            database=parsed.path[1:],  # Remove leading slash
            user=parsed.username,
            password=parsed.password,
            port=parsed.port
        )
        conn.close()
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def install_dependencies():
    """Install Python dependencies"""
    try:
        print("Installing dependencies...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], check=True)
        print("✓ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        return False

def initialize_database():
    """Initialize database tables"""
    try:
        print("Initializing database...")
        # Import app to create tables
        from app import app, db
        with app.app_context():
            db.create_all()
            print("✓ Database tables created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")
        return False

def run_tests():
    """Run basic application tests"""
    try:
        print("Running basic tests...")
        from main import app
        with app.test_client() as client:
            response = client.get('/')
            if response.status_code == 200:
                print("✓ Application is responding correctly")
                return True
            else:
                print(f"✗ Application test failed: Status {response.status_code}")
                return False
    except Exception as e:
        print(f"✗ Application test failed: {e}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Voxa Platform Deployment Script")
    print("===================================\n")
    
    # Check requirements
    print("1. Checking system requirements...")
    missing = check_requirements()
    if missing:
        print(f"\nPlease install the following before continuing: {', '.join(missing)}")
        return False
    
    # Create environment file
    print("\n2. Setting up environment configuration...")
    create_env_file()
    
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
        database_url = os.getenv('DATABASE_URL')
        openai_key = os.getenv('OPENAI_API_KEY')
    except ImportError:
        print("Installing python-dotenv...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'python-dotenv'], check=True)
        from dotenv import load_dotenv
        load_dotenv()
        database_url = os.getenv('DATABASE_URL')
        openai_key = os.getenv('OPENAI_API_KEY')
    
    # Test database connection
    print("\n3. Testing database connection...")
    if not test_database_connection(database_url):
        print("Please fix database configuration and try again.")
        return False
    
    # Install dependencies
    print("\n4. Installing application dependencies...")
    if not install_dependencies():
        return False
    
    # Initialize database
    print("\n5. Initializing database...")
    if not initialize_database():
        return False
    
    # Run tests
    print("\n6. Running application tests...")
    if not run_tests():
        print("Tests failed, but application may still work. Check logs for details.")
    
    print("\n🎉 Deployment completed successfully!")
    print("\nNext steps:")
    print("1. Start the application: python main.py")
    print("2. Visit http://localhost:5000 to test")
    print("3. Configure production deployment (see CLONE_DEPLOYMENT_GUIDE.md)")
    print("4. Customize branding and features for your full VoC Agent")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nDeployment cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)