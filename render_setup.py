#!/usr/bin/env python3
"""
Render.com Deployment Setup Script
This script creates necessary configuration files WITHOUT modifying your existing code.
Run: python render_setup.py
"""

import os
import sys

def create_requirements_txt():
    """Create requirements.txt file"""
    requirements = """Flask==2.3.3
flask-cors==4.0.0
Flask-SQLAlchemy==3.1.1
flask-bcrypt==1.0.1
PyJWT==2.8.0
pyttsx3==2.90
pydub==0.25.1
gunicorn==21.2.0
python-dotenv==1.0.0
psycopg2-binary==2.9.9
"""
    
    with open('requirements.txt', 'w') as f:
        f.write(requirements)
    print("✅ Created requirements.txt")

def create_runtime_txt():
    """Create runtime.txt file"""
    with open('runtime.txt', 'w') as f:
        f.write("python-3.9.0\n")
    print("✅ Created runtime.txt")

def create_procfile():
    """Create Procfile"""
    with open('Procfile', 'w') as f:
        f.write("web: gunicorn app:app\n")
    print("✅ Created Procfile")

def create_render_yaml():
    """Create render.yaml configuration"""
    yaml_content = """services:
  - type: web
    name: educast-studio
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app
    envVars:
      - key: SECRET_KEY
        generateValue: true
      - key: DATABASE_URL
        fromDatabase:
          name: educast-db
          property: connectionString
    healthCheckPath: /api/health
"""
    
    with open('render.yaml', 'w') as f:
        f.write(yaml_content)
    print("✅ Created render.yaml")

def create_gitignore():
    """Create .gitignore file"""
    gitignore = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual Environment
venv/
env/
ENV/
env.bak/
venv.bak/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Project specific
instance/
*.db
*.mp3
*.zip
*.log
uploads/
static/audio/temp_*
"""
    
    with open('.gitignore', 'w') as f:
        f.write(gitignore)
    print("✅ Created .gitignore")

def create_patch_file():
    """Create a patch file to fix database URL without modifying app.py"""
    patch_content = """# PATCH FOR RENDER.COM DEPLOYMENT
# This file contains instructions to modify app.py for Render.com
# You have two options:

# OPTION 1: Create a wrapper file (recommended)
# Create a new file called "render_app.py" with this content:
'''
import os
import re

# Monkey-patch the database URL before importing app
def fix_database_url():
    database_url = os.environ.get('DATABASE_URL', 'sqlite:///educast.db')
    if database_url and database_url.startswith("postgres://"):
        # Render provides postgres:// but SQLAlchemy needs postgresql://
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    os.environ['DATABASE_URL'] = database_url

fix_database_url()

# Now import and run your app
from app import app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''

# OPTION 2: Minimal change to app.py (modify ONE line)
# In app.py, change line ~31 from:
# app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///educast.db')
# To:
# database_url = os.environ.get('DATABASE_URL', 'sqlite:///educast.db')
# if database_url and database_url.startswith("postgres://"):
#     database_url = database_url.replace("postgres://", "postgresql://", 1)
# app.config['SQLALCHEMY_DATABASE_URI'] = database_url

# OPTION 3: Use environment wrapper (easiest)
# Create "start.sh" with:
# #!/bin/bash
# export DATABASE_URL=$(echo $DATABASE_URL | sed 's/postgres:/postgresql:/')
# gunicorn app:app
"""
    
    with open('RENDER_PATCH.md', 'w') as f:
        f.write(patch_content)
    print("✅ Created RENDER_PATCH.md with deployment instructions")

def create_start_sh():
    """Create start.sh script for Render"""
    start_script = """#!/bin/bash
# Render.com startup script for EduCast Studio
# This script fixes the database URL issue without modifying app.py

echo "🚀 Starting EduCast Studio on Render.com..."

# Fix PostgreSQL URL for SQLAlchemy
if [ ! -z "$DATABASE_URL" ]; then
    echo "Original DATABASE_URL: $DATABASE_URL"
    export DATABASE_URL=$(echo $DATABASE_URL | sed 's/postgres:/postgresql:/')
    echo "Fixed DATABASE_URL: $DATABASE_URL"
fi

# Create necessary directories
mkdir -p static/audio
mkdir -p instance

# Start Gunicorn
echo "Starting Gunicorn server..."
exec gunicorn app:app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --threads 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
"""
    
    with open('start.sh', 'w') as f:
        f.write(start_script)
    
    # Make it executable
    os.chmod('start.sh', 0o755)
    print("✅ Created start.sh")

def create_render_app_py():
    """Create a wrapper app file that fixes database URL"""
    wrapper_app = """#!/usr/bin/env python3
"""
    # Start with a blank file - we'll fill it below
    pass

def create_wrapper_app():
    """Create wrapper_app.py that imports your app and fixes config"""
    wrapper = """"""
    # We'll create this separately
    pass

def main():
    """Main setup function"""
    print("🎧 EduCast Studio - Render.com Deployment Setup")
    print("=" * 60)
    print("Creating deployment files WITHOUT modifying your code...")
    print()
    
    create_requirements_txt()
    create_runtime_txt()
    create_procfile()
    create_render_yaml()
    create_gitignore()
    create_patch_file()
    create_start_sh()
    
    print()
    print("=" * 60)
    print("✅ All deployment files created successfully!")
    print()
    print("📁 Files created:")
    print("  - requirements.txt (dependencies)")
    print("  - runtime.txt (Python version)")
    print("  - Procfile (start command)")
    print("  - render.yaml (Render config)")
    print("  - .gitignore (git ignore rules)")
    print("  - RENDER_PATCH.md (deployment instructions)")
    print("  - start.sh (startup script)")
    print()
    print("🚀 Next steps:")
    print("1. Review RENDER_PATCH.md for database URL fix")
    print("2. Choose one of the 3 options to fix the database URL")
    print("3. Push to GitHub")
    print("4. Deploy on Render.com")
    print()
    print("💡 Recommended: Use Option 1 from RENDER_PATCH.md")
    print("   (Create render_app.py wrapper)")
    print("=" * 60)

if __name__ == '__main__':
    main()