# PATCH FOR RENDER.COM DEPLOYMENT
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
