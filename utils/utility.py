# utils/utility.py
import re
import os
import subprocess
import shutil
import tempfile
from datetime import datetime
import json
from flask import jsonify
import jwt
import random
from typing import Dict, List, Optional, Tuple, Any
import hashlib
from pathlib import Path

# JWT Configuration (should match app.py)
JWT_SECRET_KEY = os.environ.get('SECRET_KEY', 'educast-secret-key-2023-change-in-production')
JWT_ALGORITHM = 'HS256'

# Configuration
MAX_AUDIO_DURATION = 300  # 5 minutes in seconds
DEFAULT_SPEECH_RATE = 160
DEFAULT_SPEECH_VOLUME = 0.8
SUPPORTED_AUDIO_FORMATS = ['mp3', 'wav', 'ogg']

# Book database for enhanced scripts
BOOKS_DATABASE = {
    "Pride and Prejudice": {
        "author": "Jane Austen",
        "genre": "Romance",
        "year": 1813,
        "summary": "A romantic novel of manners that satirizes issues of marriage, social status, and morality in early 19th-century England.",
        "themes": ["Love", "Social Class", "Reputation", "Marriage"],
        "characters": ["Elizabeth Bennet", "Mr. Darcy", "Jane Bennet", "Mr. Bingley"]
    },
    "The Great Gatsby": {
        "author": "F. Scott Fitzgerald",
        "genre": "Fiction",
        "year": 1925,
        "summary": "A critique of the American Dream through the story of the mysterious millionaire Jay Gatsby and his obsession with Daisy Buchanan.",
        "themes": ["American Dream", "Wealth", "Love", "Social Status"],
        "characters": ["Jay Gatsby", "Daisy Buchanan", "Nick Carraway", "Tom Buchanan"]
    },
    "Frankenstein": {
        "author": "Mary Shelley",
        "genre": "Horror",
        "year": 1818,
        "summary": "A Gothic novel exploring themes of creation, responsibility, and the consequences of scientific ambition.",
        "themes": ["Creation", "Responsibility", "Isolation", "Prejudice"],
        "characters": ["Victor Frankenstein", "The Creature", "Elizabeth Lavenza", "Henry Clerval"]
    },
    "1984": {
        "author": "George Orwell",
        "genre": "Science Fiction",
        "year": 1949,
        "summary": "A dystopian novel depicting a totalitarian society under constant surveillance and thought control.",
        "themes": ["Totalitarianism", "Surveillance", "Truth", "Freedom"],
        "characters": ["Winston Smith", "Julia", "Big Brother", "O'Brien"]
    },
    "To Kill a Mockingbird": {
        "author": "Harper Lee",
        "genre": "Fiction",
        "year": 1960,
        "summary": "A novel exploring racial injustice and moral growth through the eyes of a young girl in the American South.",
        "themes": ["Racism", "Justice", "Morality", "Childhood"],
        "characters": ["Scout Finch", "Atticus Finch", "Jem Finch", "Boo Radley"]
    }
}

# Validation functions with enhanced rules
def validate_email(email: str) -> bool:
    """Validate email address format"""
    if not email or not isinstance(email, str):
        return False
    
    email = email.strip().lower()
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> Tuple[bool, str]:
    """Validate password strength and return (is_valid, message)"""
    if not password or not isinstance(password, str):
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    # Optional: Add special character requirement
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password is valid"

def validate_name(name: str) -> Tuple[bool, str]:
    """Validate name and return (is_valid, message)"""
    if not name or not isinstance(name, str):
        return False, "Name is required"
    
    name = name.strip()
    
    if len(name) < 2:
        return False, "Name must be at least 2 characters long"
    
    if len(name) > 100:
        return False, "Name must be less than 100 characters"
    
    if not re.match(r'^[a-zA-Z\s\-\'\.]+$', name):
        return False, "Name can only contain letters, spaces, hyphens, apostrophes, and periods"
    
    return True, "Name is valid"

def validate_book_title(title: str) -> bool:
    """Validate book title"""
    return bool(title and isinstance(title, str) and 1 <= len(title.strip()) <= 200)

def validate_book_author(author: str) -> bool:
    """Validate book author"""
    return bool(author and isinstance(author, str) and 1 <= len(author.strip()) <= 200)

# Enhanced Podcast Script Generation
def generate_podcast_script(book_title: str, book_author: str = "", duration: int = 5) -> str:
    """Generate an enhanced podcast script about the book"""
    
    # Get book information from database
    book_info = BOOKS_DATABASE.get(book_title, {})
    
    # Determine number of sections based on duration
    sections = max(3, duration)
    
    # Script templates
    introductions = [
        f"Welcome to EduCast Studio's Literary Corner! Today, we're diving into '{book_title}' by {book_author or book_info.get('author', 'the author')}.",
        f"Greetings, literature lovers! In this {duration}-minute podcast, we explore the timeless classic '{book_title}'.",
        f"Hello and welcome! Join us as we unpack the themes and significance of '{book_title}' in this educational podcast.",
        f"Welcome back to EduCast! Today's episode focuses on the literary masterpiece '{book_title}'."
    ]
    
    summaries = [
        f"Published in {book_info.get('year', 'the 19th century')}, this {book_info.get('genre', 'literary')} work tells a compelling story that continues to resonate with readers today.",
        f"This {book_info.get('genre', 'classic')} novel from {book_info.get('year', 'the 1800s')} explores themes that remain relevant in our modern world.",
        f"Set against the backdrop of its historical context, '{book_title}' offers insights into human nature and society.",
        f"As a significant work in {book_info.get('genre', 'world')} literature, this book has influenced countless writers and thinkers."
    ]
    
    themes = [
        f"One of the central themes is the exploration of {random.choice(book_info.get('themes', ['human relationships', 'social structures']))}, which the author examines with remarkable depth.",
        f"The novel grapples with questions of {random.choice(book_info.get('themes', ['morality', 'identity']))}, inviting readers to reflect on their own experiences.",
        f"Through its narrative, the book addresses important issues of {random.choice(book_info.get('themes', ['justice', 'freedom']))}, making it particularly thought-provoking.",
        f"The author skillfully weaves together themes of {random.choice(book_info.get('themes', ['love', 'ambition']))}, creating a rich tapestry of meaning."
    ]
    
    characters = [
        f"The characters, particularly {random.choice(book_info.get('characters', ['the protagonist']))}, are crafted with such complexity that they feel like real people.",
        f"Readers often find themselves deeply invested in characters like {random.choice(book_info.get('characters', ['the main character']))}, whose struggles mirror our own.",
        f"The character development in '{book_title}' is exceptional, with each personality serving to illuminate different aspects of the human condition.",
        f"From {random.choice(book_info.get('characters', ['the hero']))} to the supporting cast, every character contributes meaningfully to the story's impact."
    ]
    
    significance = [
        f"What makes '{book_title}' particularly significant is its enduring relevance. The issues it raises continue to spark discussion and debate.",
        f"This book's lasting impact on literature cannot be overstated. It has shaped how we think about {book_info.get('genre', 'fiction')} writing.",
        f"Beyond its literary merits, '{book_title}' offers valuable insights into the historical and cultural context of its time.",
        f"The novel's innovative approach to storytelling has inspired generations of writers and continues to captivate new readers."
    ]
    
    educational_value = [
        f"For students and educators, '{book_title}' provides excellent material for exploring literary analysis and critical thinking skills.",
        f"The book serves as a powerful tool for discussions about {random.choice(book_info.get('themes', ['ethics', 'society']))} in educational settings.",
        f"Reading '{book_title}' can enhance understanding of literary techniques like symbolism, characterization, and narrative structure.",
        f"This work offers rich opportunities for interdisciplinary study, connecting literature with history, philosophy, and social sciences."
    ]
    
    recommendations = [
        f"If you enjoyed this podcast, I encourage you to read the complete work. The full text offers even deeper insights and appreciation.",
        f"For those interested in learning more, consider exploring critical analyses or joining a book club discussion about '{book_title}'.",
        f"After listening to this overview, you might want to create your own podcast episode or written analysis of the book's themes.",
        f"I recommend pairing your reading of '{book_title}' with historical context to better understand the author's perspective."
    ]
    
    conclusions = [
        f"Thank you for joining us on this literary exploration. Remember, every great book offers new discoveries with each reading.",
        f"That concludes our discussion of '{book_title}'. Keep exploring, keep reading, and keep learning with EduCast Studio!",
        f"We hope this podcast has inspired you to discover or revisit '{book_title}'. Until next time, happy reading!",
        f"As we wrap up, remember that literature helps us understand ourselves and our world better. Thank you for listening!"
    ]
    
    # Select random elements
    intro = random.choice(introductions)
    summary = random.choice(summaries)
    theme_analysis = random.choice(themes)
    character_analysis = random.choice(characters)
    significance_analysis = random.choice(significance)
    educational_analysis = random.choice(educational_value)
    recommendation = random.choice(recommendations)
    conclusion = random.choice(conclusions)
    
    # Build the script
    script = f"""
HOST: {intro}

HOST: {summary}

GUEST: {theme_analysis}

HOST: {character_analysis}

GUEST: {significance_analysis}

HOST: {educational_analysis}

GUEST: {recommendation}

HOST: {conclusion}
"""
    
    return script.strip()

def generate_book_summary(book_title: str, book_author: str = "") -> str:
    """Generate a concise book summary"""
    book_info = BOOKS_DATABASE.get(book_title, {})
    
    summaries = [
        f"'{book_title}' by {book_author or book_info.get('author', 'an acclaimed author')} is a {book_info.get('genre', 'literary')} work "
        f"that explores themes of {', '.join(book_info.get('themes', ['human experience']))}. "
        f"Published in {book_info.get('year', 'the 19th century')}, it remains relevant for its insights into society and human nature.",
        
        f"In '{book_title}', readers encounter a narrative that delves into {random.choice(book_info.get('themes', ['complex relationships']))}. "
        f"The novel's enduring appeal lies in its ability to connect with universal human experiences across generations.",
        
        f"This {book_info.get('genre', 'classic')} work offers a compelling examination of {random.choice(book_info.get('themes', ['moral dilemmas']))}. "
        f"The author's skillful storytelling creates a world that continues to resonate with contemporary audiences.",
        
        f"'{book_title}' stands as a significant contribution to literature, particularly in its treatment of "
        f"{random.choice(book_info.get('themes', ['social issues']))}. Its characters and themes have become part of our cultural conversation."
    ]
    
    return random.choice(summaries)

# Enhanced Audio Generation
def generate_audio_with_pyttsx3(script: str, output_file: str, voice_type: str = "default") -> Tuple[bool, str]:
    """Generate audio using pyttsx3 text-to-speech with enhanced options"""
    try:
        import pyttsx3
        
        engine = pyttsx3.init()
        
        # Set speech properties
        engine.setProperty('rate', DEFAULT_SPEECH_RATE)
        engine.setProperty('volume', DEFAULT_SPEECH_VOLUME)
        
        # Configure voice based on type
        voices = engine.getProperty('voices')
        if voices:
            if voice_type == "male" and len(voices) > 0:
                engine.setProperty('voice', voices[0].id)
            elif voice_type == "female" and len(voices) > 1:
                engine.setProperty('voice', voices[1].id)
            elif voice_type == "alternate" and len(voices) > 2:
                engine.setProperty('voice', voices[2].id)
        
        # Split script into segments for better processing
        segments = script.split('\n\n')
        temp_files = []
        
        for i, segment in enumerate(segments):
            if segment.strip():
                temp_file = f"{output_file}.part{i}.mp3"
                engine.save_to_file(segment.strip(), temp_file)
                temp_files.append(temp_file)
        
        engine.runAndWait()
        
        # Combine all segments
        if len(temp_files) > 1:
            combine_audio_files(temp_files, output_file)
        elif temp_files:
            shutil.move(temp_files[0], output_file)
        
        # Clean up temporary files
        for temp_file in temp_files:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
        
        return True, "Audio generated successfully"
        
    except ImportError:
        return False, "pyttsx3 library not installed"
    except Exception as e:
        return False, f"pyttsx3 error: {str(e)}"

def combine_audio_files(input_files: List[str], output_file: str) -> bool:
    """Combine multiple audio files into one"""
    try:
        # Create a temporary file list
        list_file = output_file + '.txt'
        with open(list_file, 'w') as f:
            for input_file in input_files:
                f.write(f"file '{input_file}'\n")
        
        # Use ffmpeg to combine
        subprocess.run([
            'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
            '-i', list_file, '-c', 'copy', output_file
        ], check=True, capture_output=True)
        
        # Clean up
        if os.path.exists(list_file):
            os.remove(list_file)
        
        return True
    except Exception:
        return False

def limit_audio_duration(audio_file: str, max_duration: int = MAX_AUDIO_DURATION) -> Tuple[bool, float]:
    """Limit audio duration to maximum specified seconds and return actual duration"""
    try:
        # Get current duration
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', audio_file
        ], capture_output=True, text=True)
        
        if result.returncode != 0:
            return False, 0
        
        duration = float(result.stdout.strip())
        
        # Trim if necessary
        if duration > max_duration:
            temp_file = audio_file + '.trimmed.mp3'
            subprocess.run([
                'ffmpeg', '-y', '-i', audio_file, '-t', str(max_duration),
                '-c', 'copy', temp_file
            ], check=True, capture_output=True)
            
            shutil.move(temp_file, audio_file)
            return True, max_duration
        
        return True, duration
        
    except Exception as e:
        return False, 0

def normalize_audio_volume(audio_file: str) -> bool:
    """Normalize audio volume using ffmpeg"""
    try:
        temp_file = audio_file + '.normalized.mp3'
        
        subprocess.run([
            'ffmpeg', '-y', '-i', audio_file,
            '-filter:a', 'loudnorm',
            '-c:a', 'libmp3lame', '-q:a', '2',
            temp_file
        ], check=True, capture_output=True)
        
        shutil.move(temp_file, audio_file)
        return True
    except Exception:
        return False

# File Management Utilities
def generate_filename(prefix: str, extension: str = 'mp3') -> str:
    """Generate a unique filename"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    random_str = hashlib.md5(str(datetime.now().timestamp()).encode()).hexdigest()[:8]
    return f"{prefix}_{timestamp}_{random_str}.{extension}"

def get_file_size(filepath: str) -> int:
    """Get file size in bytes"""
    try:
        return os.path.getsize(filepath)
    except:
        return 0

def get_audio_duration(filepath: str) -> float:
    """Get audio duration in seconds"""
    try:
        result = subprocess.run([
            'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1', filepath
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    return 0.0

def cleanup_temp_files(directory: str, pattern: str = "*") -> None:
    """Clean up temporary files"""
    try:
        for file in Path(directory).glob(pattern):
            if file.is_file():
                file.unlink()
    except:
        pass

# Response Helper Functions
def success_response(data: Optional[Dict] = None, message: str = "Success", status_code: int = 200, **kwargs):
    """Generate success response"""
    response = {
        'status': 'success',
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'version': '1.2.0'
    }
    
    if data:
        response['data'] = data
    
    # Add any additional kwargs
    response.update(kwargs)
    
    return jsonify(response), status_code

def error_response(message: str = "Error", status_code: int = 400, errors: Optional[List] = None):
    """Generate error response"""
    response = {
        'status': 'error',
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
        'code': status_code
    }
    
    if errors:
        response['errors'] = errors
    
    return jsonify(response), status_code

def validation_error_response(errors: Dict[str, List[str]]) -> Tuple:
    """Generate validation error response"""
    error_list = []
    for field, messages in errors.items():
        for message in messages:
            error_list.append({
                'field': field,
                'message': message
            })
    
    return error_response(
        message="Validation failed",
        status_code=422,
        errors=error_list
    )

# JWT Token Utilities
def create_jwt_token(user_id: int, role: str, email: str, expiration_hours: int = 24) -> str:
    """Create JWT token"""
    payload = {
        'user_id': user_id,
        'role': role,
        'email': email,
        'exp': datetime.utcnow().timestamp() + (expiration_hours * 3600),
        'iat': datetime.utcnow().timestamp(),
        'iss': 'educast-studio'
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token: str) -> Optional[Dict]:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

def decode_auth_header(auth_header: str) -> Optional[Dict]:
    """Decode JWT from Authorization header"""
    if not auth_header or not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header.split(' ')[1]
    return verify_jwt_token(token)

# Text Processing Utilities
def truncate_text(text: str, max_length: int = 500, suffix: str = "...") -> str:
    """Truncate text to specified length"""
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def word_count(text: str) -> int:
    """Count words in text"""
    if not text:
        return 0
    return len(text.split())

def estimate_reading_time(text: str, words_per_minute: int = 200) -> int:
    """Estimate reading time in minutes"""
    words = word_count(text)
    return max(1, words // words_per_minute)

# Data Formatting Utilities
def format_duration(seconds: float) -> str:
    """Format duration in seconds to human-readable string"""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds > 0:
            return f"{int(minutes)} min {int(remaining_seconds)} sec"
        return f"{int(minutes)} min"
    else:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{int(hours)} hr {int(minutes)} min"

def format_file_size(bytes_size: int) -> str:
    """Format file size in bytes to human-readable string"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

# Security Utilities
def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent directory traversal"""
    # Remove directory components
    filename = os.path.basename(filename)
    
    # Remove potentially dangerous characters
    filename = re.sub(r'[^\w\-_.]', '', filename)
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename

def validate_file_extension(filename: str, allowed_extensions: List[str]) -> bool:
    """Validate file extension"""
    if not filename:
        return False
    
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in allowed_extensions

# Podcast Specific Utilities
def generate_podcast_metadata(book_title: str, script: str, duration: float) -> Dict:
    """Generate podcast metadata"""
    return {
        'title': f"EduCast: {book_title}",
        'description': f"An educational podcast exploring {book_title}",
        'author': "EduCast Studio",
        'duration': format_duration(duration),
        'word_count': word_count(script),
        'reading_time': estimate_reading_time(script),
        'generated_at': datetime.utcnow().isoformat()
    }

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text"""
    # Remove common stop words and punctuation
    stop_words = {'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
    
    words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
    word_freq = {}
    
    for word in words:
        if word not in stop_words:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Sort by frequency and return top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:max_keywords]]

# Logging Utilities
class Logger:
    """Simple logger for utility functions"""
    
    @staticmethod
    def info(message: str):
        print(f"[INFO] {datetime.now().isoformat()} - {message}")
    
    @staticmethod
    def error(message: str):
        print(f"[ERROR] {datetime.now().isoformat()} - {message}")
    
    @staticmethod
    def warn(message: str):
        print(f"[WARN] {datetime.now().isoformat()} - {message}")

# Main execution guard
if __name__ == "__main__":
    # Test utility functions
    print("Testing utility functions...")
    
    # Test validation
    print(f"Email validation: {validate_email('test@example.com')}")
    
    is_valid, msg = validate_password("StrongPass123!")
    print(f"Password validation: {is_valid} - {msg}")
    
    # Test script generation
    script = generate_podcast_script("Pride and Prejudice", "Jane Austen")
    print(f"Generated script length: {len(script)} characters")
    
    # Test JWT
    token = create_jwt_token(1, "user", "test@example.com")
    print(f"JWT Token created: {bool(token)}")
    
    print("Utility functions test completed!")