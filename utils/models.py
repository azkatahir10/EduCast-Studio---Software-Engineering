# utils/models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from sqlalchemy.orm import validates
import re

db = SQLAlchemy()

class User(db.Model):
    """User model for authentication and profile management"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='user', nullable=False)  # 'user' or 'admin'
    
    # Profile fields
    bio = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(255), nullable=True)
    preferences = db.Column(db.Text, nullable=True)  # JSON string for user preferences
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    last_logout = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    podcasts = db.relationship('Podcast', backref='user', lazy=True, cascade='all, delete-orphan')
    favorite_books = db.relationship('FavoriteBook', backref='user', lazy=True, cascade='all, delete-orphan')
    chat_history = db.relationship('ChatHistory', backref='user', lazy=True, cascade='all, delete-orphan')
    
    # Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    
    @validates('email')
    def validate_email(self, key, email):
        if not email:
            raise ValueError('Email is required')
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValueError('Invalid email format')
        return email.lower()
    
    @validates('role')
    def validate_role(self, key, role):
        if role not in ['user', 'admin']:
            raise ValueError('Role must be either "user" or "admin"')
        return role
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'preferences': self.preferences,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'is_active': self.is_active,
            'is_verified': self.is_verified,
            'stats': {
                'podcast_count': len(self.podcasts),
                'favorite_count': len(self.favorite_books)
            }
        }
    
    def __repr__(self):
        return f'<User {self.email}>'

class Podcast(db.Model):
    """Podcast model for generated audio content"""
    __tablename__ = 'podcasts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Book information
    book_id = db.Column(db.Integer, nullable=False, index=True)
    book_title = db.Column(db.String(200), nullable=False)
    book_author = db.Column(db.String(200), nullable=False)
    
    # Podcast metadata
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # Audio file information
    audio_url = db.Column(db.String(500), nullable=True)
    file_size = db.Column(db.Integer, nullable=True)  # in bytes
    duration = db.Column(db.String(20), nullable=False)  # e.g., "5 min"
    format = db.Column(db.String(10), default='mp3', nullable=False)
    
    # Generation settings
    script = db.Column(db.Text, nullable=True)
    language = db.Column(db.String(50), default='English', nullable=False)
    tone = db.Column(db.String(50), default='educational', nullable=False)
    speed = db.Column(db.Float, default=1.0, nullable=False)  # playback speed
    
    # Generation status
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, processing, completed, failed
    progress = db.Column(db.Integer, default=0, nullable=False)  # 0-100 percentage
    error_message = db.Column(db.Text, nullable=True)
    
    # Statistics
    play_count = db.Column(db.Integer, default=0, nullable=False)
    like_count = db.Column(db.Integer, default=0, nullable=False)
    download_count = db.Column(db.Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Metadata
    tags = db.Column(db.Text, nullable=True)  # comma-separated tags
    is_public = db.Column(db.Boolean, default=False, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_podcast_user_status', 'user_id', 'status'),
        db.Index('idx_podcast_created', 'created_at'),
        db.Index('idx_podcast_book', 'book_id'),
    )
    
    @validates('status')
    def validate_status(self, key, status):
        valid_statuses = ['pending', 'processing', 'completed', 'failed', 'cancelled']
        if status not in valid_statuses:
            raise ValueError(f'Status must be one of: {valid_statuses}')
        return status
    
    @validates('progress')
    def validate_progress(self, key, progress):
        if not 0 <= progress <= 100:
            raise ValueError('Progress must be between 0 and 100')
        return progress
    
    def to_dict(self):
        """Convert podcast object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'book_title': self.book_title,
            'book_author': self.book_author,
            'title': self.title,
            'description': self.description,
            'audio_url': self.audio_url,
            'file_size': self.file_size,
            'duration': self.duration,
            'format': self.format,
            'language': self.language,
            'tone': self.tone,
            'speed': self.speed,
            'status': self.status,
            'progress': self.progress,
            'error_message': self.error_message,
            'play_count': self.play_count,
            'like_count': self.like_count,
            'download_count': self.download_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'tags': self.tags.split(',') if self.tags else [],
            'is_public': self.is_public,
            'script_preview': self.script[:200] + '...' if self.script and len(self.script) > 200 else self.script
        }
    
    def increment_play_count(self):
        """Increment play count"""
        self.play_count += 1
        db.session.commit()
    
    def increment_like_count(self):
        """Increment like count"""
        self.like_count += 1
        db.session.commit()
    
    def increment_download_count(self):
        """Increment download count"""
        self.download_count += 1
        db.session.commit()
    
    def __repr__(self):
        return f'<Podcast {self.title}>'

class FavoriteBook(db.Model):
    """Model for user's favorite books"""
    __tablename__ = 'favorite_books'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    book_id = db.Column(db.Integer, nullable=False, index=True)
    
    # Additional metadata
    notes = db.Column(db.Text, nullable=True)
    rating = db.Column(db.Integer, nullable=True)  # 1-5 stars
    last_read = db.Column(db.DateTime, nullable=True)
    
    # Timestamps
    added_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Composite unique constraint
    __table_args__ = (
        db.UniqueConstraint('user_id', 'book_id', name='unique_user_book'),
    )
    
    @validates('rating')
    def validate_rating(self, key, rating):
        if rating is not None and not 1 <= rating <= 5:
            raise ValueError('Rating must be between 1 and 5')
        return rating
    
    def to_dict(self):
        """Convert favorite book to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'book_id': self.book_id,
            'notes': self.notes,
            'rating': self.rating,
            'last_read': self.last_read.isoformat() if self.last_read else None,
            'added_at': self.added_at.isoformat() if self.added_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<FavoriteBook user_id={self.user_id} book_id={self.book_id}>'

class ChatHistory(db.Model):
    """Model for storing chat history between users and AI"""
    __tablename__ = 'chat_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Message content
    message = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, default=True, nullable=False)  # True for user, False for AI
    
    # Context metadata
    context_type = db.Column(db.String(50), nullable=True)  # e.g., 'book_discussion', 'podcast_generation'
    context_id = db.Column(db.Integer, nullable=True)  # ID of related book or podcast
    session_id = db.Column(db.String(100), nullable=True, index=True)  # To group messages in a session
    
    # Response metadata (for AI messages)
    response_time = db.Column(db.Float, nullable=True)  # in seconds
    model_used = db.Column(db.String(50), nullable=True)
    
    # User feedback
    is_helpful = db.Column(db.Boolean, nullable=True)
    user_feedback = db.Column(db.Text, nullable=True)
    
    # Timestamps
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_chat_user_timestamp', 'user_id', 'timestamp'),
        db.Index('idx_chat_session', 'session_id'),
    )
    
    def to_dict(self):
        """Convert chat message to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'message': self.message,
            'is_user': self.is_user,
            'context_type': self.context_type,
            'context_id': self.context_id,
            'session_id': self.session_id,
            'response_time': self.response_time,
            'model_used': self.model_used,
            'is_helpful': self.is_helpful,
            'user_feedback': self.user_feedback,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }
    
    def __repr__(self):
        return f'<ChatHistory {"User" if self.is_user else "AI"}: {self.message[:50]}>'

class BookMetadata(db.Model):
    """Model for storing additional book metadata (optional enhancement)"""
    __tablename__ = 'book_metadata'
    
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    
    # Enhanced metadata
    summary = db.Column(db.Text, nullable=True)
    themes = db.Column(db.Text, nullable=True)  # comma-separated themes
    characters = db.Column(db.Text, nullable=True)  # comma-separated characters
    historical_context = db.Column(db.Text, nullable=True)
    critical_reception = db.Column(db.Text, nullable=True)
    
    # Educational value
    reading_level = db.Column(db.String(50), nullable=True)  # e.g., 'High School', 'College'
    educational_topics = db.Column(db.Text, nullable=True)  # comma-separated topics
    
    # External references
    wikipedia_url = db.Column(db.String(500), nullable=True)
    project_gutenberg_id = db.Column(db.String(50), nullable=True)
    goodreads_id = db.Column(db.String(50), nullable=True)
    
    # Statistics
    view_count = db.Column(db.Integer, default=0, nullable=False)
    podcast_count = db.Column(db.Integer, default=0, nullable=False)  # Number of podcasts generated
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        """Convert book metadata to dictionary"""
        return {
            'id': self.id,
            'book_id': self.book_id,
            'summary': self.summary,
            'themes': self.themes.split(',') if self.themes else [],
            'characters': self.characters.split(',') if self.characters else [],
            'historical_context': self.historical_context,
            'critical_reception': self.critical_reception,
            'reading_level': self.reading_level,
            'educational_topics': self.educational_topics.split(',') if self.educational_topics else [],
            'wikipedia_url': self.wikipedia_url,
            'project_gutenberg_id': self.project_gutenberg_id,
            'goodreads_id': self.goodreads_id,
            'view_count': self.view_count,
            'podcast_count': self.podcast_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<BookMetadata book_id={self.book_id}>'

class UserActivity(db.Model):
    """Model for tracking user activity (optional enhancement)"""
    __tablename__ = 'user_activity'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Activity details
    activity_type = db.Column(db.String(50), nullable=False)  # e.g., 'login', 'podcast_generated', 'book_viewed'
    activity_details = db.Column(db.Text, nullable=True)  # JSON string with details
    
    # Resource reference
    resource_type = db.Column(db.String(50), nullable=True)  # e.g., 'book', 'podcast'
    resource_id = db.Column(db.Integer, nullable=True)
    
    # Device/IP info (for security)
    ip_address = db.Column(db.String(45), nullable=True)  # Supports IPv6
    user_agent = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        db.Index('idx_activity_user_type', 'user_id', 'activity_type'),
        db.Index('idx_activity_timestamp', 'created_at'),
    )
    
    def to_dict(self):
        """Convert activity to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'activity_type': self.activity_type,
            'activity_details': self.activity_details,
            'resource_type': self.resource_type,
            'resource_id': self.resource_id,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<UserActivity {self.activity_type} for user {self.user_id}>'

# Database initialization function
def init_db(app):
    """Initialize database with app context"""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully!")
        
        # Create indexes if they don't exist
        from sqlalchemy import inspect, Index
        inspector = inspect(db.engine)
        
        # Check and create composite indexes
        existing_indexes = inspector.get_indexes('podcasts')
        index_names = [idx['name'] for idx in existing_indexes]
        
        # Create additional indexes if needed
        if 'idx_podcast_user_status' not in index_names:
            idx = Index('idx_podcast_user_status', Podcast.user_id, Podcast.status)
            idx.create(db.engine)
            print("Created idx_podcast_user_status index")
        
        print("Database initialization complete!")