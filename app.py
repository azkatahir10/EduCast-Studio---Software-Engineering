from flask import Flask, request, jsonify, send_from_directory, render_template, make_response
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from datetime import datetime, timedelta
import os
import tempfile
import shutil
import jwt  # Using PyJWT instead of Flask-JWT-Extended
import secrets
from functools import wraps
import traceback

from utils.models import db, User, Podcast, FavoriteBook, ChatHistory
from utils.utility import (
    validate_email, validate_password, validate_name,
    generate_podcast_script, generate_audio_with_pyttsx3, limit_audio_duration,
    success_response, error_response, generate_book_summary,
    truncate_text, format_duration, format_file_size,
    create_jwt_token as util_create_jwt_token,
    verify_jwt_token as util_verify_jwt_token,
    decode_auth_header
)

app = Flask(__name__, template_folder='templates')

# Enhanced configuration with environment variables
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'educast-secret-key-2023-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///educast.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'static/audio'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['JWT_EXPIRATION_HOURS'] = 24

# Initialize extensions
db.init_app(app)
bcrypt = Bcrypt(app)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# JWT Configuration
JWT_SECRET_KEY = app.config['SECRET_KEY']
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION = int(app.config['JWT_EXPIRATION_HOURS'])

# Create JWT token
def create_jwt_token(user_id, role, email):
    payload = {
        'user_id': user_id,
        'role': role,
        'email': email,
        'exp': datetime.utcnow() + timedelta(hours=JWT_EXPIRATION),
        'iat': datetime.utcnow(),
        'jti': secrets.token_hex(16)  # Unique token ID
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

# Verify JWT token
def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

# Get current user from token
def get_current_user():
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return None
    
    token = token.split(' ')[1]
    payload = verify_jwt_token(token)
    if not payload:
        return None
    
    return User.query.get(payload['user_id'])

# Enhanced authentication decorator with role checking
def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return error_response('Authentication required. Please login.', 401)
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
        if user.role != 'admin':
            return error_response('Admin access required', 403)
        return f(*args, **kwargs)
    return decorated_function

# Create upload directory
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Routes for HTML pages
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/collections')
def collections():
    return render_template('collections.html')

@app.route('/favourites')
def favourites():
    return render_template('favourites.html')

@app.route('/podcast-generation')
def podcast_generation():
    return render_template('podcast_generation.html')

@app.route('/chat')
def chat():
    return render_template('chat.html')

@app.route('/authentication')
def authentication():
    return render_template('authentication.html')

@app.route('/admin')
@admin_required
def admin_panel():
    return render_template('admin.html')

# API Routes
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['name', 'email', 'password']):
            return error_response('All fields are required', 400)
        
        name = data['name'].strip()
        email = data['email'].strip().lower()
        password = data['password']
        
        is_valid_name, name_message = validate_name(name)
        if not is_valid_name:
            return error_response(name_message, 400)
        
        if not validate_email(email):
            return error_response('Please provide a valid email address', 400)
        
        is_valid_password, password_message = validate_password(password)
        if not is_valid_password:
            return error_response(password_message, 400)
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return error_response('User already exists with this email', 409)
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(
            name=name,
            email=email,
            password=hashed_password,
            role='user',
            created_at=datetime.utcnow()
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Create token for immediate login
        token = create_jwt_token(user.id, user.role, user.email)
        
        return success_response({
            'user': user.to_dict(),
            'token': token
        }, 'User registered successfully', 201)
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Registration error: {str(e)}')
        return error_response(f'Error creating user: {str(e)}', 500)

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['email', 'password']):
            return error_response('Email and password are required', 400)
        
        email = data['email'].strip().lower()
        password = data['password']
        
        if not validate_email(email):
            return error_response('Please provide a valid email address', 400)
        
        user = User.query.filter_by(email=email).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # Create JWT token
            token = create_jwt_token(user.id, user.role, user.email)
            
            return success_response({
                'token': token,
                'role': user.role,
                'user': user.to_dict()
            }, 'Login successful')
        else:
            return error_response('Invalid email or password', 401)
            
    except Exception as e:
        app.logger.error(f'Login error: {str(e)}')
        return error_response(f'Login error: {str(e)}', 500)

@app.route('/api/validate-token', methods=['POST'])
def validate_token():
    """Validate JWT token"""
    try:
        data = request.get_json()
        token = data.get('token', '')
        
        if not token:
            return error_response('Token is required', 400)
        
        payload = verify_jwt_token(token)
        if not payload:
            return error_response('Invalid or expired token', 401)
        
        user = User.query.get(payload['user_id'])
        if not user:
            return error_response('User not found', 404)
        
        return success_response({
            'valid': True,
            'user': user.to_dict(),
            'expires': payload['exp']
        }, 'Token is valid')
        
    except Exception as e:
        return error_response(f'Token validation error: {str(e)}', 500)

@app.route('/api/logout', methods=['POST'])
@jwt_required
def logout():
    try:
        user = get_current_user()
        if user:
            user.last_logout = datetime.utcnow()
            db.session.commit()
        
        return success_response({}, 'Logged out successfully')
    except Exception as e:
        return error_response(f'Logout error: {str(e)}', 500)

@app.route('/api/check-email', methods=['POST'])
def check_email():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not validate_email(email):
            return error_response('Invalid email format')
        
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            return success_response({'exists': True}, 'Email already registered')
        else:
            return success_response({'exists': False}, 'Email available')
            
    except Exception as e:
        app.logger.error(f'Check email error: {str(e)}')
        return error_response(str(e), 500)

@app.route('/api/profile', methods=['GET'])
@jwt_required
def profile():
    try:
        user = get_current_user()
        
        if not user:
            return error_response('User not found', 404)
        
        return success_response({'user': user.to_dict()}, 'Profile retrieved')
        
    except Exception as e:
        app.logger.error(f'Profile fetch error: {str(e)}')
        return error_response(f'Error fetching profile: {str(e)}', 500)

@app.route('/api/profile', methods=['PUT'])
@jwt_required
def update_profile():
    try:
        user = get_current_user()
        if not user:
            return error_response('User not found', 404)
        
        data = request.get_json()
        
        if 'name' in data:
            name = data['name'].strip()
            if validate_name(name):
                user.name = name
        
        if 'email' in data:
            email = data['email'].strip().lower()
            if validate_email(email) and email != user.email:
                existing = User.query.filter_by(email=email).first()
                if existing:
                    return error_response('Email already in use', 409)
                user.email = email
        
        if 'bio' in data:
            user.bio = data['bio'][:500] if data['bio'] else None
        
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return success_response({'user': user.to_dict()}, 'Profile updated successfully')
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error updating profile: {str(e)}', 500)

@app.route('/api/change-password', methods=['POST'])
@jwt_required
def change_password():
    try:
        user = get_current_user()
        if not user:
            return error_response('User not found', 404)
        
        data = request.get_json()
        
        if not all(key in data for key in ['current_password', 'new_password']):
            return error_response('Current and new password required', 400)
        
        if not bcrypt.check_password_hash(user.password, data['current_password']):
            return error_response('Current password is incorrect', 401)
        
        is_valid, message = validate_password(data['new_password'])
        if not is_valid:
            return error_response(message, 400)
        
        user.password = bcrypt.generate_password_hash(data['new_password']).decode('utf-8')
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        return success_response({}, 'Password changed successfully')
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error changing password: {str(e)}', 500)

# Book Collections API - Fixed endpoint
@app.route('/api/books', methods=['GET'])
@jwt_required
def get_books():
    """Get book collection with filtering and pagination"""
    try:
        # Get query parameters with defaults
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 12))
        genre = request.args.get('genre', '').strip().lower()
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort_by', 'popularity')
        sort_order = request.args.get('sort_order', 'desc')
        
        # Define the books database
        books_db = [
            {
                "id": 1,
                "title": "Pride and Prejudice",
                "author": "Jane Austen",
                "year": 1813,
                "genre": "Romance",
                "description": "A romantic novel of manners that depicts the emotional development of protagonist Elizabeth Bennet.",
                "source": "Standard Ebooks",
                "popularity": 98,
                "coverUrl": "https://covers.openlibrary.org/b/id/8312261-M.jpg",
                "pdfUrl": "https://standardebooks.org/ebooks/jane-austen/pride-and-prejudice/downloads/jane-austen_pride-and-prejudice.epub",
                "summary": "A classic novel exploring themes of love, reputation, and class in early 19th-century England.",
                "language": "English",
                "pages": 432,
                "rating": 4.7,
                "isFavorite": False
            },
            {
                "id": 2,
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "year": 1925,
                "genre": "Fiction",
                "description": "A story of the mysteriously wealthy Jay Gatsby and his love for the beautiful Daisy Buchanan.",
                "source": "Public Domain",
                "popularity": 93,
                "coverUrl": "https://covers.openlibrary.org/b/id/8226451-M.jpg",
                "pdfUrl": None,
                "summary": "An exploration of the American Dream, wealth, and social status during the Jazz Age.",
                "language": "English",
                "pages": 218,
                "rating": 4.5,
                "isFavorite": False
            },
            {
                "id": 3,
                "title": "Frankenstein",
                "author": "Mary Shelley",
                "year": 1818,
                "genre": "Horror",
                "description": "A story about Victor Frankenstein, a young scientist who creates a sapient creature in an unorthodox scientific experiment.",
                "source": "Standard Ebooks",
                "popularity": 92,
                "coverUrl": "https://covers.openlibrary.org/b/id/8231789-M.jpg",
                "pdfUrl": "https://standardebooks.org/ebooks/mary-shelley/frankenstein/downloads/mary-shelley_frankenstein.epub",
                "summary": "A Gothic novel that examines themes of creation, responsibility, and the consequences of playing God.",
                "language": "English",
                "pages": 280,
                "rating": 4.6,
                "isFavorite": False
            },
            {
                "id": 4,
                "title": "1984",
                "author": "George Orwell",
                "year": 1949,
                "genre": "Science Fiction",
                "description": "A dystopian social science fiction novel about totalitarian control and thought control.",
                "source": "Public Domain",
                "popularity": 96,
                "coverUrl": "https://covers.openlibrary.org/b/id/7222246-M.jpg",
                "pdfUrl": None,
                "summary": "A chilling depiction of a totalitarian future society under constant surveillance.",
                "language": "English",
                "pages": 328,
                "rating": 4.8,
                "isFavorite": False
            },
            {
                "id": 5,
                "title": "To Kill a Mockingbird",
                "author": "Harper Lee",
                "year": 1960,
                "genre": "Fiction",
                "description": "A novel about racial inequality and moral growth in the American South.",
                "source": "Public Domain",
                "popularity": 94,
                "coverUrl": "https://covers.openlibrary.org/b/id/8305837-M.jpg",
                "pdfUrl": None,
                "summary": "A powerful exploration of racial injustice and moral growth in the American South.",
                "language": "English",
                "pages": 324,
                "rating": 4.8,
                "isFavorite": False
            },
            {
                "id": 6,
                "title": "Wuthering Heights",
                "author": "Emily Brontë",
                "year": 1847,
                "genre": "Gothic Fiction",
                "description": "A story of the intense, almost demonic love between Catherine Earnshaw and Heathcliff.",
                "source": "Public Domain",
                "popularity": 88,
                "coverUrl": "https://covers.openlibrary.org/b/id/8041460-M.jpg",
                "pdfUrl": None,
                "summary": "A tale of obsessive love and revenge set on the Yorkshire moors.",
                "language": "English",
                "pages": 416,
                "rating": 4.4,
                "isFavorite": False
            },
            {
                "id": 7,
                "title": "Jane Eyre",
                "author": "Charlotte Brontë",
                "year": 1847,
                "genre": "Romance",
                "description": "A novel about an orphan girl's growth to adulthood and her love for Mr. Rochester.",
                "source": "Public Domain",
                "popularity": 91,
                "coverUrl": "https://covers.openlibrary.org/b/id/8226512-M.jpg",
                "pdfUrl": None,
                "summary": "A coming-of-age story exploring love, independence, and morality.",
                "language": "English",
                "pages": 532,
                "rating": 4.6,
                "isFavorite": False
            },
            {
                "id": 8,
                "title": "Brave New World",
                "author": "Aldous Huxley",
                "year": 1932,
                "genre": "Science Fiction",
                "description": "A dystopian novel about a technologically advanced future society.",
                "source": "Public Domain",
                "popularity": 89,
                "coverUrl": "https://covers.openlibrary.org/b/id/8181921-M.jpg",
                "pdfUrl": None,
                "summary": "A vision of a future where technology and conditioning control human society.",
                "language": "English",
                "pages": 268,
                "rating": 4.5,
                "isFavorite": False
            },
            {
                "id": 9,
                "title": "Moby Dick",
                "author": "Herman Melville",
                "year": 1851,
                "genre": "Adventure",
                "description": "The voyage of the whaling ship Pequod, commanded by Captain Ahab in search of the white whale.",
                "source": "Public Domain",
                "popularity": 87,
                "coverUrl": "https://covers.openlibrary.org/b/id/8226458-M.jpg",
                "pdfUrl": None,
                "summary": "An epic tale of obsession, revenge, and man's struggle against nature.",
                "language": "English",
                "pages": 635,
                "rating": 4.3,
                "isFavorite": False
            },
            {
                "id": 10,
                "title": "The Catcher in the Rye",
                "author": "J.D. Salinger",
                "year": 1951,
                "genre": "Fiction",
                "description": "Story of Holden Caulfield's experiences in New York City after being expelled from prep school.",
                "source": "Public Domain",
                "popularity": 90,
                "coverUrl": "https://covers.openlibrary.org/b/id/8226486-M.jpg",
                "pdfUrl": None,
                "summary": "A novel about teenage alienation and loss of innocence.",
                "language": "English",
                "pages": 277,
                "rating": 4.1,
                "isFavorite": False
            },
            {
                "id": 11,
                "title": "The Hobbit",
                "author": "J.R.R. Tolkien",
                "year": 1937,
                "genre": "Fantasy",
                "description": "The adventure of Bilbo Baggins as he travels with a group of dwarves to reclaim their mountain home.",
                "source": "Public Domain",
                "popularity": 95,
                "coverUrl": "https://covers.openlibrary.org/b/id/8226534-M.jpg",
                "pdfUrl": None,
                "summary": "A fantasy novel that serves as a prelude to The Lord of the Rings.",
                "language": "English",
                "pages": 310,
                "rating": 4.8,
                "isFavorite": False
            },
            {
                "id": 12,
                "title": "The Picture of Dorian Gray",
                "author": "Oscar Wilde",
                "year": 1890,
                "genre": "Philosophical Fiction",
                "description": "A novel about a handsome young man who sells his soul for eternal youth and beauty.",
                "source": "Public Domain",
                "popularity": 86,
                "coverUrl": "https://covers.openlibrary.org/b/id/8226548-M.jpg",
                "pdfUrl": None,
                "summary": "An exploration of aestheticism, morality, and the nature of beauty.",
                "language": "English",
                "pages": 254,
                "rating": 4.4,
                "isFavorite": False
            }
        ]
        
        # Apply filters
        filtered_books = books_db
        
        if genre and genre != 'all':
            filtered_books = [book for book in filtered_books if book['genre'].lower() == genre]
        
        if search:
            search_lower = search.lower()
            filtered_books = [
                book for book in filtered_books
                if search_lower in book['title'].lower() or 
                   search_lower in book['author'].lower() or
                   search_lower in book['genre'].lower() or
                   (book['description'] and search_lower in book['description'].lower())
            ]
        
        # Apply sorting
        reverse_order = (sort_order == 'desc')
        
        if sort_by == 'title':
            filtered_books.sort(key=lambda x: x['title'].lower(), reverse=reverse_order)
        elif sort_by == 'author':
            filtered_books.sort(key=lambda x: x['author'].lower(), reverse=reverse_order)
        elif sort_by == 'year':
            filtered_books.sort(key=lambda x: x['year'], reverse=reverse_order)
        elif sort_by == 'popularity':
            filtered_books.sort(key=lambda x: x['popularity'], reverse=reverse_order)
        elif sort_by == 'rating':
            filtered_books.sort(key=lambda x: x['rating'], reverse=reverse_order)
        
        # Apply pagination
        total_books = len(filtered_books)
        total_pages = (total_books + per_page - 1) // per_page
        
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page
        paginated_books = filtered_books[start_idx:end_idx]
        
        # Get available genres for filter
        genres = list(set(book['genre'] for book in books_db))
        genres.sort()
        
        return success_response({
            'books': paginated_books,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total_books': total_books,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            },
            'filters': {
                'genres': genres,
                'applied_genre': genre,
                'applied_search': search,
                'applied_sort': sort_by,
                'applied_sort_order': sort_order
            }
        }, 'Books retrieved successfully')
        
    except ValueError as e:
        return error_response(f'Invalid parameter value: {str(e)}', 400)
    except Exception as e:
        app.logger.error(f'Books fetch error: {str(e)}')
        app.logger.error(traceback.format_exc())
        return error_response(f'Error fetching books: {str(e)}', 500)

@app.route('/api/books/<int:book_id>', methods=['GET'])
@jwt_required
def get_book(book_id):
    """Get a specific book by ID"""
    try:
        # Get all books
        books_db = [
            {
                "id": 1,
                "title": "Pride and Prejudice",
                "author": "Jane Austen",
                "year": 1813,
                "genre": "Romance",
                "description": "A romantic novel of manners that depicts the emotional development of protagonist Elizabeth Bennet.",
                "source": "Standard Ebooks",
                "popularity": 98,
                "coverUrl": "https://covers.openlibrary.org/b/id/8312261-M.jpg",
                "pdfUrl": "https://standardebooks.org/ebooks/jane-austen/pride-and-prejudice/downloads/jane-austen_pride-and-prejudice.epub",
                "summary": "A classic novel exploring themes of love, reputation, and class in early 19th-century England.",
                "language": "English",
                "pages": 432,
                "rating": 4.7,
                "isFavorite": False
            },
            {
                "id": 2,
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "year": 1925,
                "genre": "Fiction",
                "description": "A story of the mysteriously wealthy Jay Gatsby and his love for the beautiful Daisy Buchanan.",
                "source": "Public Domain",
                "popularity": 93,
                "coverUrl": "https://covers.openlibrary.org/b/id/8226451-M.jpg",
                "pdfUrl": None,
                "summary": "An exploration of the American Dream, wealth, and social status during the Jazz Age.",
                "language": "English",
                "pages": 218,
                "rating": 4.5,
                "isFavorite": False
            },
            {
                "id": 3,
                "title": "Frankenstein",
                "author": "Mary Shelley",
                "year": 1818,
                "genre": "Horror",
                "description": "A story about Victor Frankenstein, a young scientist who creates a sapient creature in an unorthodox scientific experiment.",
                "source": "Standard Ebooks",
                "popularity": 92,
                "coverUrl": "https://covers.openlibrary.org/b/id/8231789-M.jpg",
                "pdfUrl": "https://standardebooks.org/ebooks/mary-shelley/frankenstein/downloads/mary-shelley_frankenstein.epub",
                "summary": "A Gothic novel that examines themes of creation, responsibility, and the consequences of playing God.",
                "language": "English",
                "pages": 280,
                "rating": 4.6,
                "isFavorite": False
            },
            # Add more books as needed...
        ]
        
        book = next((b for b in books_db if b['id'] == book_id), None)
        
        if not book:
            return error_response('Book not found', 404)
        
        return success_response({'book': book}, 'Book retrieved successfully')
        
    except Exception as e:
        return error_response(f'Error fetching book: {str(e)}', 500)

@app.route('/api/books/genres', methods=['GET'])
@jwt_required
def get_genres():
    """Get all available genres"""
    try:
        books_db = [
            {"id": 1, "genre": "Romance"},
            {"id": 2, "genre": "Fiction"},
            {"id": 3, "genre": "Horror"},
            {"id": 4, "genre": "Science Fiction"},
            {"id": 5, "genre": "Fiction"},
            {"id": 6, "genre": "Gothic Fiction"},
            {"id": 7, "genre": "Romance"},
            {"id": 8, "genre": "Science Fiction"},
            {"id": 9, "genre": "Adventure"},
            {"id": 10, "genre": "Fiction"},
            {"id": 11, "genre": "Fantasy"},
            {"id": 12, "genre": "Philosophical Fiction"}
        ]
        
        genres = list(set(book['genre'] for book in books_db))
        genres.sort()
        
        return success_response({'genres': genres}, 'Genres retrieved successfully')
        
    except Exception as e:
        return error_response(f'Error fetching genres: {str(e)}', 500)

# Podcast Generation API with enhanced features - FIXED VERSION
@app.route('/api/generate-podcast', methods=['POST'])
@jwt_required
def generate_podcast():
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
            
        data = request.get_json()
        
        # Check required fields
        required_fields = ['book_id', 'title', 'author']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return error_response(f'Missing required fields: {", ".join(missing_fields)}', 400)
        
        book_id = data['book_id']
        title = data['title'].strip()
        author = data['author'].strip()
        
        if not title:
            return error_response('Book title cannot be empty', 400)
        
        if not author:
            return error_response('Author cannot be empty', 400)
        
        # Check if podcast already exists for this book
        existing_podcast = Podcast.query.filter_by(
            user_id=user.id, 
            book_id=book_id
        ).first()
        
        if existing_podcast:
            return success_response(
                {'podcast': existing_podcast.to_dict()},
                'Podcast for this book already exists'
            )
        
        # Generate script with enhanced content
        duration = data.get('duration', 5)
        if not isinstance(duration, (int, float)) or duration <= 0:
            duration = 5
        
        script = generate_podcast_script(title, author, duration)
        
        # Create podcast record with all required fields
        podcast = Podcast(
            user_id=user.id,
            book_id=book_id,
            book_title=title,
            book_author=author,
            title=f"EduCast: {title}",
            description=data.get('description', f'A {duration}-minute podcast about {title} by {author}'),
            status='pending',
            progress=0,
            duration=f"{duration} min",  # Ensure duration is set
            format='mp3',
            language=data.get('language', 'English'),
            tone=data.get('tone', 'educational'),
            speed=data.get('speed', 1.0),
            tags=data.get('tags', ''),  # Ensure tags is empty string if not provided
            is_public=data.get('is_public', False),
            created_at=datetime.utcnow(),
            script=script  # Set script initially
        )
        
        db.session.add(podcast)
        db.session.commit()  # Commit first to get the ID
        
        # Start background generation
        import threading
        thread = threading.Thread(
            target=generate_podcast_audio_background,
            args=(podcast.id, script, duration)
        )
        thread.daemon = True
        thread.start()
        
        # Update status to processing (no need to commit again)
        podcast.status = 'processing'
        podcast.progress = 10
        db.session.commit()
        
        return success_response({
            'podcast': podcast.to_dict(),
            'message': 'Podcast generation started',
            'estimated_time': f'Approximately {duration * 2} seconds'
        }, 'Podcast generation started successfully')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Podcast generation error: {str(e)}')
        app.logger.error(traceback.format_exc())
        return error_response(f'Error creating podcast: {str(e)}', 500)

def generate_podcast_audio_background(podcast_id, script, duration_minutes):
    """Background task to generate podcast audio - FIXED VERSION"""
    try:
        with app.app_context():
            podcast = Podcast.query.get(podcast_id)
            if not podcast:
                return
            
            temp_dir = tempfile.mkdtemp()
            output_file = os.path.join(temp_dir, f"podcast_{podcast.id}.mp3")
            
            # Update progress and ensure all fields are set
            podcast.progress = 30
            podcast.script = script  # Make sure script is set
            podcast.duration = f"{duration_minutes} min"  # Make sure duration is set
            podcast.tags = podcast.tags if podcast.tags else ""  # Ensure tags is not None
            db.session.commit()
            
            # Generate audio
            success, message = generate_audio_with_pyttsx3(script, output_file, podcast.tone)
            
            if success:
                # Update progress
                podcast.progress = 70
                db.session.commit()
                
                # Limit duration
                max_duration = duration_minutes * 60  # Convert to seconds
                success_duration, actual_duration = limit_audio_duration(output_file, max_duration)
                
                if success_duration and os.path.exists(output_file):
                    # Move to final location
                    final_filename = f"podcast_{podcast.id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.mp3"
                    final_filepath = os.path.join(app.config['UPLOAD_FOLDER'], final_filename)
                    
                    # Ensure directory exists
                    os.makedirs(os.path.dirname(final_filepath), exist_ok=True)
                    shutil.move(output_file, final_filepath)
                    
                    # Update podcast record
                    podcast.audio_url = f"/static/audio/{final_filename}"
                    podcast.file_size = os.path.getsize(final_filepath) if os.path.exists(final_filepath) else 0
                    podcast.status = 'completed'
                    podcast.progress = 100
                    podcast.completed_at = datetime.utcnow()
                else:
                    podcast.status = 'failed'
                    podcast.error_message = 'Audio duration limitation failed'
            else:
                podcast.status = 'failed'
                podcast.error_message = f'Audio generation failed: {message}'
            
            db.session.commit()
            
            # Clean up temp directory
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
                
    except Exception as e:
        app.logger.error(f'Background audio generation error: {str(e)}')
        app.logger.error(traceback.format_exc())
        if 'podcast' in locals():
            podcast.status = 'failed'
            podcast.error_message = str(e)
            # Ensure all required fields are set even on error
            podcast.duration = podcast.duration if podcast.duration else f"{duration_minutes} min"
            podcast.tags = podcast.tags if podcast.tags else ""
            db.session.commit()

@app.route('/api/podcasts', methods=['GET'])
@jwt_required
def get_user_podcasts():
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
            
        status = request.args.get('status')
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 10)), 50)
        
        query = Podcast.query.filter_by(user_id=user.id)
        
        if status and status != 'all':
            query = query.filter_by(status=status)
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * per_page
        podcasts = query.order_by(Podcast.created_at.desc()).offset(offset).limit(per_page).all()
        
        # Convert to dict with safe handling
        podcasts_list = []
        for podcast in podcasts:
            try:
                podcasts_list.append(podcast.to_dict())
            except Exception as e:
                app.logger.error(f'Error converting podcast {podcast.id} to dict: {str(e)}')
                # Create a safe version
                podcasts_list.append({
                    'id': podcast.id,
                    'title': podcast.title or 'Unknown',
                    'status': podcast.status,
                    'error': 'Error loading podcast details'
                })
        
        return success_response({
            'podcasts': podcasts_list,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page,
                'has_next': offset + per_page < total,
                'has_prev': page > 1
            }
        }, 'Podcasts retrieved successfully')
        
    except Exception as e:
        app.logger.error(f'Podcasts fetch error: {str(e)}')
        return error_response(f'Error fetching podcasts: {str(e)}', 500)

@app.route('/api/podcast/<int:podcast_id>', methods=['GET'])
@jwt_required
def get_podcast(podcast_id):
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
            
        podcast = Podcast.query.filter_by(id=podcast_id, user_id=user.id).first()
        
        if not podcast:
            return error_response('Podcast not found', 404)
        
        # Increment play count if requested
        if request.args.get('play', '').lower() == 'true':
            podcast.increment_play_count()
        
        try:
            podcast_dict = podcast.to_dict()
        except Exception as e:
            app.logger.error(f'Error converting podcast to dict: {str(e)}')
            # Return basic info if to_dict fails
            podcast_dict = {
                'id': podcast.id,
                'title': podcast.title or 'Unknown',
                'status': podcast.status,
                'error_message': podcast.error_message,
                'created_at': podcast.created_at.isoformat() if podcast.created_at else None
            }
        
        # Add formatted file size if available
        if podcast.file_size:
            podcast_dict['file_size_formatted'] = format_file_size(podcast.file_size)
        
        return success_response({'podcast': podcast_dict}, 'Podcast retrieved')
        
    except Exception as e:
        app.logger.error(f'Podcast fetch error: {str(e)}')
        return error_response(f'Error fetching podcast: {str(e)}', 500)

@app.route('/api/podcast/<int:podcast_id>', methods=['DELETE'])
@jwt_required
def delete_podcast(podcast_id):
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
            
        podcast = Podcast.query.filter_by(id=podcast_id, user_id=user.id).first()
        
        if not podcast:
            return error_response('Podcast not found', 404)
        
        # Delete audio file if it exists
        if podcast.audio_url:
            try:
                filename = podcast.audio_url.replace('/static/audio/', '')
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                app.logger.error(f'File deletion error: {str(e)}')
        
        db.session.delete(podcast)
        db.session.commit()
        
        return success_response(
            {'deleted_id': podcast_id},
            'Podcast deleted successfully'
        )
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Podcast deletion error: {str(e)}')
        return error_response(f'Error deleting podcast: {str(e)}', 500)

@app.route('/api/podcast/<int:podcast_id>/like', methods=['POST'])
@jwt_required
def like_podcast(podcast_id):
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
            
        podcast = Podcast.query.filter_by(id=podcast_id).first()
        
        if not podcast:
            return error_response('Podcast not found', 404)
        
        podcast.increment_like_count()
        
        return success_response(
            {'likes': podcast.like_count},
            'Podcast liked successfully'
        )
        
    except Exception as e:
        return error_response(f'Error liking podcast: {str(e)}', 500)

# Favorites API with database integration
@app.route('/api/favorites/books', methods=['GET'])
@jwt_required
def get_favorite_books():
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
            
        # Get favorite books from database
        favorites = FavoriteBook.query.filter_by(user_id=user.id).all()
        favorite_ids = [fav.book_id for fav in favorites]
        
        # Get all books (simplified for this example)
        all_books = [
            {
                "id": 1,
                "title": "Pride and Prejudice",
                "author": "Jane Austen",
                "genre": "Romance",
                "popularity": 98,
                "coverUrl": "https://covers.openlibrary.org/b/id/8312261-M.jpg"
            },
            {
                "id": 2,
                "title": "The Great Gatsby",
                "author": "F. Scott Fitzgerald",
                "genre": "Fiction",
                "popularity": 93,
                "coverUrl": "https://covers.openlibrary.org/b/id/8226451-M.jpg"
            },
            {
                "id": 3,
                "title": "Frankenstein",
                "author": "Mary Shelley",
                "genre": "Horror",
                "popularity": 92,
                "coverUrl": "https://covers.openlibrary.org/b/id/8231789-M.jpg"
            }
        ]
        
        # Filter favorite books
        favorite_books = [book for book in all_books if book['id'] in favorite_ids]
        
        # Mark as favorite
        for book in favorite_books:
            book['isFavorite'] = True
        
        return success_response({
            'books': favorite_books,
            'count': len(favorite_books)
        }, 'Favorite books retrieved')
        
    except Exception as e:
        app.logger.error(f'Favorite books fetch error: {str(e)}')
        return error_response(f'Error fetching favorite books: {str(e)}', 500)

@app.route('/api/favorites/books/<int:book_id>', methods=['POST'])
@jwt_required
def add_favorite_book(book_id):
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
        
        # Check if already favorited
        existing = FavoriteBook.query.filter_by(user_id=user.id, book_id=book_id).first()
        if existing:
            return success_response({}, 'Book already in favorites')
        
        # Verify book exists (simplified check)
        if not 1 <= book_id <= 12:  # Adjust based on your book IDs
            return error_response('Book not found', 404)
        
        favorite = FavoriteBook(
            user_id=user.id, 
            book_id=book_id, 
            added_at=datetime.utcnow()
        )
        db.session.add(favorite)
        db.session.commit()
        
        return success_response({
            'book_id': book_id,
            'added': True
        }, 'Book added to favorites', 201)
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error adding favorite: {str(e)}', 500)

@app.route('/api/favorites/books/<int:book_id>', methods=['DELETE'])
@jwt_required
def remove_favorite_book(book_id):
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
        
        favorite = FavoriteBook.query.filter_by(user_id=user.id, book_id=book_id).first()
        if not favorite:
            return error_response('Favorite not found', 404)
        
        db.session.delete(favorite)
        db.session.commit()
        
        return success_response({
            'book_id': book_id,
            'removed': True
        }, 'Book removed from favorites')
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error removing favorite: {str(e)}', 500)

# Chat API with history
@app.route('/api/chat', methods=['POST'])
@jwt_required
def chat_with_ai():
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
            
        data = request.get_json()
        message = data.get('message', '').strip()
        
        if not message:
            return error_response('Message cannot be empty', 400)
        
        # Generate session ID if not provided
        session_id = data.get('session_id') or secrets.token_hex(8)
        
        # Save user message to history
        user_message = ChatHistory(
            user_id=user.id,
            message=message,
            is_user=True,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        db.session.add(user_message)
        db.session.flush()
        
        # Generate AI response
        ai_response = generate_ai_response(message, user)
        
        # Save AI response to history
        ai_message = ChatHistory(
            user_id=user.id,
            message=ai_response,
            is_user=False,
            session_id=session_id,
            timestamp=datetime.utcnow()
        )
        db.session.add(ai_message)
        
        db.session.commit()
        
        return success_response({
            'response': ai_response,
            'message_id': ai_message.id,
            'session_id': session_id
        }, 'AI response generated')
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Chat error: {str(e)}')
        return error_response(f'Error processing chat: {str(e)}', 500)

def generate_ai_response(message: str, user) -> str:
    """Generate AI response based on user message and context"""
    import random
    
    # Check if message is about a specific book
    book_keywords = {
        'pride': 'Pride and Prejudice',
        'prejudice': 'Pride and Prejudice',
        'gatsby': 'The Great Gatsby',
        'frankenstein': 'Frankenstein',
        '1984': '1984',
        'mockingbird': 'To Kill a Mockingbird',
        'wuthering': 'Wuthering Heights',
        'jane eyre': 'Jane Eyre',
        'brave new world': 'Brave New World',
        'moby': 'Moby Dick',
        'catcher': 'The Catcher in the Rye',
        'hobbit': 'The Hobbit',
        'dorian gray': 'The Picture of Dorian Gray'
    }
    
    message_lower = message.lower()
    book_mentioned = None
    
    for keyword, book_title in book_keywords.items():
        if keyword in message_lower:
            book_mentioned = book_title
            break
    
    if book_mentioned:
        summary = generate_book_summary(book_mentioned)
        responses = [
            f"I see you're asking about '{book_mentioned}'. {summary}\n\nWould you like me to help you generate a podcast episode about this book?",
            f"Ah, '{book_mentioned}' is a fascinating work! {summary}\n\nI can help you create an educational podcast about it if you're interested.",
            f"That's an excellent choice! '{book_mentioned}' has so much to explore. {summary}\n\nWould you like to discuss specific themes or generate a podcast?",
            f"I'm glad you mentioned '{book_mentioned}'! {summary}\n\nThis would make a great topic for an EduCast podcast episode."
        ]
        return random.choice(responses)
    
    # Check for podcast-related queries
    podcast_keywords = ['podcast', 'audio', 'generate', 'create', 'record', 'listen']
    if any(keyword in message_lower for keyword in podcast_keywords):
        responses = [
            "I can help you generate podcasts from books in our collection! Just select a book and choose 'Generate Podcast'.",
            "To create a podcast, go to the Collections page, select a book, and click the Generate Podcast button. I'll help you create a 5-minute educational episode!",
            "Podcast generation is one of my specialties! Choose any book from our collection, and I'll help you create an engaging audio episode about it.",
            "I'd love to help you create a podcast! Browse our book collection, pick one that interests you, and use the podcast generation feature."
        ]
        return random.choice(responses)
    
    # General responses
    responses = [
        f"I understand you're asking about: '{message}'. As your EduCast assistant, I can help you with:\n"
        "• Book recommendations and summaries\n"
        "• Podcast generation from books\n"
        "• Literary analysis and discussions\n"
        "• Finding books by genre or author\n\n"
        "What would you like to explore today?",
        
        f"Interesting question about: '{message}'. Have you checked our book collections? "
        "I can help you find related titles or generate a podcast episode about this topic.",
        
        f"Regarding '{message}', this relates to many classic works in our collection. "
        "Would you like me to suggest some books or help you create educational content about it?",
        
        f"Great question! '{message}' is an excellent topic for discussion. "
        "I can help you explore this through our book collection or by generating a podcast episode. "
        "What specifically interests you about this topic?"
    ]
    
    return random.choice(responses)

@app.route('/api/chat/history', methods=['GET'])
@jwt_required
def get_chat_history():
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
        
        limit = min(int(request.args.get('limit', 50)), 100)
        session_id = request.args.get('session_id')
        
        query = ChatHistory.query.filter_by(user_id=user.id)
        
        if session_id:
            query = query.filter_by(session_id=session_id)
        
        history = query.order_by(ChatHistory.timestamp.asc()).limit(limit).all()
        
        return success_response({
            'history': [{
                'id': msg.id,
                'message': msg.message,
                'is_user': msg.is_user,
                'session_id': msg.session_id,
                'timestamp': msg.timestamp.isoformat() if msg.timestamp else None
            } for msg in history]
        }, 'Chat history retrieved')
        
    except Exception as e:
        return error_response(f'Error fetching chat history: {str(e)}', 500)

@app.route('/api/chat/history/<string:session_id>', methods=['DELETE'])
@jwt_required
def clear_chat_session(session_id):
    try:
        user = get_current_user()
        if not user:
            return error_response('Authentication required', 401)
        
        ChatHistory.query.filter_by(user_id=user.id, session_id=session_id).delete()
        db.session.commit()
        
        return success_response({}, 'Chat session cleared')
        
    except Exception as e:
        db.session.rollback()
        return error_response(f'Error clearing chat session: {str(e)}', 500)

# Admin API endpoints
@app.route('/api/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        
        offset = (page - 1) * per_page
        users = User.query.order_by(User.created_at.desc()).offset(offset).limit(per_page).all()
        total = User.query.count()
        
        return success_response({
            'users': [user.to_dict() for user in users],
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }, 'Users retrieved successfully')
        
    except Exception as e:
        return error_response(f'Error fetching users: {str(e)}', 500)

@app.route('/api/admin/podcasts', methods=['GET'])
@admin_required
def get_all_podcasts():
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 20)), 100)
        status = request.args.get('status')
        
        query = Podcast.query.join(User)
        
        if status and status != 'all':
            query = query.filter(Podcast.status == status)
        
        total = query.count()
        offset = (page - 1) * per_page
        
        podcasts = query.order_by(Podcast.created_at.desc()).offset(offset).limit(per_page).all()
        
        result = []
        for podcast in podcasts:
            try:
                podcast_dict = podcast.to_dict()
                podcast_dict['user_name'] = podcast.user.name
                podcast_dict['user_email'] = podcast.user.email
                result.append(podcast_dict)
            except Exception as e:
                app.logger.error(f'Error converting podcast {podcast.id} to dict: {str(e)}')
                result.append({
                    'id': podcast.id,
                    'title': podcast.title or 'Unknown',
                    'status': podcast.status,
                    'user_name': podcast.user.name if podcast.user else 'Unknown',
                    'error': 'Error loading podcast details'
                })
        
        return success_response({
            'podcasts': result,
            'pagination': {
                'current_page': page,
                'per_page': per_page,
                'total': total,
                'total_pages': (total + per_page - 1) // per_page
            }
        }, 'All podcasts retrieved successfully')
        
    except Exception as e:
        return error_response(f'Error fetching podcasts: {str(e)}', 500)

@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    try:
        total_users = User.query.count()
        total_podcasts = Podcast.query.count()
        completed_podcasts = Podcast.query.filter_by(status='completed').count()
        
        # Active users (logged in within last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        active_users = User.query.filter(
            User.last_login >= thirty_days_ago
        ).count()
        
        # Recent activity
        recent_podcasts = Podcast.query.order_by(
            Podcast.created_at.desc()
        ).limit(5).all()
        
        recent_users = User.query.order_by(
            User.created_at.desc()
        ).limit(5).all()
        
        # Calculate success rate
        success_rate = 0
        if total_podcasts > 0:
            success_rate = (completed_podcasts / total_podcasts) * 100
        
        # Convert podcasts to dict safely
        recent_podcasts_list = []
        for podcast in recent_podcasts:
            try:
                recent_podcasts_list.append(podcast.to_dict())
            except Exception as e:
                recent_podcasts_list.append({
                    'id': podcast.id,
                    'title': podcast.title or 'Unknown',
                    'status': podcast.status
                })
        
        return success_response({
            'stats': {
                'total_users': total_users,
                'total_podcasts': total_podcasts,
                'completed_podcasts': completed_podcasts,
                'active_users': active_users,
                'success_rate': round(success_rate, 1)
            },
            'recent_podcasts': recent_podcasts_list,
            'recent_users': [user.to_dict() for user in recent_users]
        }, 'Admin statistics retrieved')
        
    except Exception as e:
        return error_response(f'Error fetching stats: {str(e)}', 500)

# Serve static audio files
@app.route('/static/audio/<filename>')
def serve_audio_file(filename):
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except Exception as e:
        return error_response(f'Audio file not found: {str(e)}', 404)

# Health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        # Check database connection
        db.session.execute('SELECT 1')
        
        # Check upload directory
        upload_dir_exists = os.path.exists(app.config['UPLOAD_FOLDER'])
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.2.0',
            'services': {
                'database': 'connected',
                'audio_storage': 'available' if upload_dir_exists else 'unavailable'
            }
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# System status endpoint
@app.route('/api/status', methods=['GET'])
def system_status():
    """Get system status information"""
    try:
        import platform
        import sys
        
        return success_response({
            'system': {
                'platform': platform.platform(),
                'python_version': sys.version,
                'flask_version': '2.3.2',
                'environment': 'development' if app.debug else 'production'
            },
            'application': {
                'name': 'EduCast Studio',
                'version': '1.2.0',
                'uptime': 'N/A'  # Could implement with startup time tracking
            },
            'database': {
                'type': 'SQLite',
                'connected': True,
                'user_count': User.query.count(),
                'podcast_count': Podcast.query.count()
            }
        }, 'System status retrieved')
    except Exception as e:
        return error_response(f'Error getting system status: {str(e)}', 500)

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return error_response('Resource not found', 404)

@app.errorhandler(405)
def method_not_allowed(error):
    return error_response('Method not allowed', 405)

@app.errorhandler(500)
def internal_error(error):
    app.logger.error(f'Server error: {str(error)}')
    app.logger.error(traceback.format_exc())
    return error_response('Internal server error', 500)

@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all unhandled exceptions"""
    app.logger.error(f'Unhandled exception: {str(error)}')
    app.logger.error(traceback.format_exc())
    return error_response('An unexpected error occurred', 500)

# Initialize database
def initialize_database():
    with app.app_context():
        db.create_all()
        
        # Create default admin user if not exists
        admin_email = 'admin@educast.com'
        existing_admin = User.query.filter_by(email=admin_email).first()
        if not existing_admin:
            hashed_password = bcrypt.generate_password_hash('Admin@123').decode('utf-8')
            admin_user = User(
                name='System Administrator',
                email=admin_email,
                password=hashed_password,
                role='admin',
                created_at=datetime.utcnow(),
                is_active=True,
                is_verified=True
            )
            db.session.add(admin_user)
            print(f"✓ Created default admin user: {admin_email}")
        
        # Create test user if not exists
        test_email = 'user@educast.com'
        existing_test_user = User.query.filter_by(email=test_email).first()
        if not existing_test_user:
            hashed_password = bcrypt.generate_password_hash('User@123').decode('utf-8')
            test_user = User(
                name='Test User',
                email=test_email,
                password=hashed_password,
                role='user',
                created_at=datetime.utcnow(),
                is_active=True,
                is_verified=True
            )
            db.session.add(test_user)
            print(f"✓ Created test user: {test_email}")
        
        db.session.commit()
        print("✓ Database initialized successfully!")

if __name__ == '__main__':
    # Initialize database before starting
    print("\n" + "=" * 60)
    print("🎧 EduCast Studio - Enhanced Edition")
    print("=" * 60)
    
    print("\n🔧 Initializing system...")
    try:
        initialize_database()
    except Exception as e:
        print(f"⚠️ Database initialization warning: {str(e)}")
        print("Continuing with existing database...")
    
    print("\n✨ Features:")
    print("-" * 30)
    print("✅ Enhanced JWT authentication")
    print("✅ Role-based access control (User/Admin)")
    print("✅ 12+ books with cover images")
    print("✅ Advanced filtering and pagination")
    print("✅ Background podcast generation")
    print("✅ Chat with AI assistant")
    print("✅ Favorite books management")
    print("✅ Admin dashboard with statistics")
    print("✅ Comprehensive error handling")
    
    print("\n🔑 Default Credentials:")
    print("-" * 30)
    print("Admin: admin@educast.com / Admin@123")
    print("User:  user@educast.com  / User@123")
    
    print("\n📚 Available Books:")
    print("-" * 30)
    print("1. Pride and Prejudice")
    print("2. The Great Gatsby")
    print("3. Frankenstein")
    print("4. 1984")
    print("5. To Kill a Mockingbird")
    print("6. Wuthering Heights")
    print("7. Jane Eyre")
    print("8. Brave New World")
    print("9. Moby Dick")
    print("10. The Catcher in the Rye")
    print("11. The Hobbit")
    print("12. The Picture of Dorian Gray")
    
    print("\n🚀 Starting server...")
    print("Open your browser and go to: http://localhost:5000")
    
    print("\n📚 Available Pages:")
    print("  - Home: http://localhost:5000")
    print("  - Collections: http://localhost:5000/collections")
    print("  - Favorites: http://localhost:5000/favourites")
    print("  - Podcast Generation: http://localhost:5000/podcast-generation")
    print("  - Chat: http://localhost:5000/chat")
    print("  - Authentication: http://localhost:5000/authentication")
    print("  - Admin Panel: http://localhost:5000/admin (Admin only)")
    
    print("\n⚡ API Endpoints:")
    print("  - Health Check: http://localhost:5000/api/health")
    print("  - Books: http://localhost:5000/api/books")
    print("  - User Profile: http://localhost:5000/api/profile")
    print("  - Generate Podcast: http://localhost:5000/api/generate-podcast")
    print("  - Chat: http://localhost:5000/api/chat")
    
    print("\n🔧 Configuration:")
    print(f"  - Database: {app.config['SQLALCHEMY_DATABASE_URI']}")
    print(f"  - Upload Folder: {app.config['UPLOAD_FOLDER']}")
    print(f"  - JWT Expiration: {JWT_EXPIRATION} hours")
    print(f"  - Debug Mode: {app.debug}")
    
    print("\n📊 Database Stats:")
    with app.app_context():
        try:
            user_count = User.query.count()
            podcast_count = Podcast.query.count()
            print(f"  - Total Users: {user_count}")
            print(f"  - Total Podcasts: {podcast_count}")
        except:
            print("  - Stats: Could not retrieve")
    
    print("\n🔒 Security Notes:")
    print("  - All passwords are securely hashed")
    print("  - JWT tokens expire after 24 hours")
    print("  - API endpoints require authentication")
    print("  - Admin endpoints require admin role")
    
    print("\n🔄 Server Information:")
    print("  - Port: 5000")
    print("  - Press Ctrl+C to stop the server")
    
    print("\n" + "=" * 60)
    print("Server is now running! 🚀")
    print("=" * 60)
    
    # Start the Flask development server
    app.run(
        debug=True, 
        port=5000, 
        host='0.0.0.0',
        threaded=True
    )