#!/usr/bin/env python3
"""
EduCast Studio - Render.com Entry Point
This is the main file that Render will run.
It fixes the database URL issue WITHOUT modifying your original app.py
"""

import os
import re

print("=" * 60)
print("🎧 EduCast Studio - Render.com Deployment")
print("=" * 60)

# Fix database URL for Render.com PostgreSQL
database_url = os.environ.get('DATABASE_URL', 'sqlite:///educast.db')

if database_url and database_url.startswith("postgres://"):
    # SQLAlchemy requires postgresql://, not postgres://
    database_url = database_url.replace("postgres://", "postgresql://", 1)
    os.environ['DATABASE_URL'] = database_url
    print(f"✅ Fixed PostgreSQL URL for SQLAlchemy")

# Set production environment
os.environ['FLASK_ENV'] = 'production'
os.environ['PYTHONUNBUFFERED'] = 'TRUE'

print(f"📊 Database: {database_url.split('@')[-1] if '@' in database_url else 'SQLite'}")
print(f"🌐 Port: {os.environ.get('PORT', 5000)}")
print(f"🔧 Environment: {os.environ.get('FLASK_ENV', 'production')}")

# Create necessary directories
os.makedirs('static/audio', exist_ok=True)
os.makedirs('instance', exist_ok=True)

print("📁 Created necessary directories")
print("=" * 60)

# Now import and run your ACTUAL app
print("🚀 Importing EduCast Studio application...")

# Import your original app
from app import app

# Override the database URL in app's config (without modifying app.py)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url

print("✅ App configured with fixed database URL")
print("=" * 60)

# The actual app will be run by Gunicorn
# This file just sets up the environment

if __name__ == '__main__':
    # This runs when testing locally
    port = int(os.environ.get('PORT', 5000))
    print(f"🌍 Starting development server on port {port}...")
    print(f"👉 Open http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)