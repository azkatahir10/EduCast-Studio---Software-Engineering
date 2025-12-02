#!/usr/bin/env python3
"""
Database URL fix for Render.com deployment
Run this BEFORE starting your app on Render
Add this to your Procfile: web: python fix_database.py && gunicorn app:app
"""

import os
import re

def fix_database_url():
    """Fix the database URL for SQLAlchemy on Render.com"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url and database_url.startswith("postgres://"):
        # SQLAlchemy needs postgresql://, not postgres://
        fixed_url = database_url.replace("postgres://", "postgresql://", 1)
        os.environ['DATABASE_URL'] = fixed_url
        print(f"✅ Fixed database URL for SQLAlchemy")
        print(f"   Original: {database_url[:50]}...")
        print(f"   Fixed:    {fixed_url[:50]}...")
    else:
        print(f"✅ Using database URL: {database_url or 'sqlite:///educast.db (default)'}")
    
    return os.environ['DATABASE_URL']

if __name__ == '__main__':
    # Fix the URL
    fix_database_url()
    
    # Now import and run the actual app
    print("🚀 Starting EduCast Studio...")
    
    # Import after fixing environment
    from app import app
    
    # Get port from environment
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)