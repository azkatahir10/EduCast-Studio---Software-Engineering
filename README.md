```markdown
# 🎧 EduCast Studio

An interactive educational platform that transforms classic literature into podcast experiences using automated text-to-speech generation.

## ✨ Features

### 📚 Book Collection
- Browse 12+ classic literary works
- Filter books by genre (Romance, Fiction, Horror, Sci-Fi, etc.)
- Search books by title, author, or description
- Sort by popularity, rating, year, or title
- View detailed book information with summaries

### 🎙️ Podcast Generation
- Convert book content into audio podcasts
- Customizable podcast duration
- Background audio processing
- Download generated podcasts
- View podcast generation history

### 💬 AI Chat Assistant
- Chat about classic literature
- Get book recommendations
- Learn about authors and themes
- Context-aware responses for 12+ literary works

### ❤️ Personalization
- Add/remove books to favorites
- Track listening history
- Manage your podcast library
- User profile management

### 🔐 User Authentication
- Secure user registration and login
- JWT-based authentication
- Password hashing with bcrypt
- Profile management

## 🚀 Quick Start

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd educast-studio
```

2. **Set up virtual environment**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

If `requirements.txt` is missing, install manually:
```bash
pip install flask flask-sqlalchemy flask-cors flask-bcrypt pyjwt pyttsx3
```

4. **Initialize the database**
```bash
python
>>> from app import db, app
>>> with app.app_context():
>>>     db.create_all()
>>> exit()
```

5. **Run the application**
```bash
python app.py
```

6. **Open in browser**
Navigate to `http://localhost:5000`

## 📁 Project Structure

```
educast-studio/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── instance/
│   └── educast.db         # SQLite database
├── static/
│   └── audio/             # Generated podcast files
├── templates/             # HTML templates
│   ├── home.html
│   ├── collections.html
│   ├── favourites.html
│   ├── podcast_generation.html
│   ├── chat.html
│   └── authentication.html
└── utils/
    ├── models.py          # Database models
    └── utility.py         # Helper functions
```

## 🌐 Application Pages

### Home (`/`)
Welcome page with platform overview

### Collections (`/collections`)
Browse and search all available books

### Favourites (`/favourites`)
View and manage your favorite books

### Podcast Generation (`/podcast-generation`)
Generate podcasts from selected books

### Chat (`/chat`)
Interact with the AI literary assistant

### Authentication (`/authentication`)
User login and registration

## 🔧 API Endpoints

### Authentication
- `POST /api/register` - Register new user
- `POST /api/login` - User login
- `POST /api/validate-token` - Validate JWT token
- `POST /api/logout` - User logout

### User Profile
- `GET /api/profile` - Get user profile
- `PUT /api/profile` - Update profile
- `POST /api/change-password` - Change password
- `POST /api/check-email` - Check email availability

### Books
- `GET /api/books` - Get all books with filtering
- `GET /api/books/<id>` - Get specific book
- `GET /api/books/genres` - Get all genres

### Podcasts
- `POST /api/generate-podcast` - Generate new podcast
- `GET /api/podcasts` - Get user's podcasts
- `GET /api/podcast/<id>` - Get specific podcast
- `POST /api/podcast/<id>/like` - Like a podcast
- `DELETE /api/podcast/<id>` - Delete podcast

### Favorites
- `GET /api/favorites/books` - Get favorite books
- `POST /api/favorites/books/<id>` - Add to favorites
- `DELETE /api/favorites/books/<id>` - Remove from favorites

### Chat
- `POST /api/chat` - Send message to AI assistant
- `GET /api/chat/history` - Get chat history
- `DELETE /api/chat/history/<session_id>` - Clear chat session

### System
- `GET /api/health` - Health check
- `GET /api/status` - System status

## 👥 Default Users

### Test User
- **Email:** user@educast.com
- **Password:** User@123

### Create New User
You can also register a new account through the authentication page.

## 📚 Available Books

1. **Pride and Prejudice** by Jane Austen (Romance)
2. **The Great Gatsby** by F. Scott Fitzgerald (Fiction)
3. **Frankenstein** by Mary Shelley (Horror)
4. **1984** by George Orwell (Science Fiction)
5. **To Kill a Mockingbird** by Harper Lee (Fiction)
6. **Wuthering Heights** by Emily Brontë (Gothic Fiction)
7. **Jane Eyre** by Charlotte Brontë (Romance)
8. **Brave New World** by Aldous Huxley (Science Fiction)
9. **Moby Dick** by Herman Melville (Adventure)
10. **The Catcher in the Rye** by J.D. Salinger (Fiction)
11. **The Hobbit** by J.R.R. Tolkien (Fantasy)
12. **The Picture of Dorian Gray** by Oscar Wilde (Philosophical Fiction)

## 🛠️ Technical Details

### Backend
- **Framework:** Flask
- **Database:** SQLite with SQLAlchemy ORM
- **Authentication:** JWT with bcrypt hashing
- **Text-to-Speech:** pyttsx3

### Frontend
- **Templates:** HTML with Jinja2
- **Styling:** CSS
- **JavaScript:** Vanilla JS for interactivity

### Key Features
- RESTful API design
- Background audio processing
- File upload and management
- Session-based chat
- Responsive design

## 🔍 Usage Guide

### 1. Getting Started
1. Register a new account or login with test credentials
2. Browse the book collection
3. Select a book to view details

### 2. Generating a Podcast
1. Go to Podcast Generation page
2. Select a book from your collection
3. Set duration (default: 5 minutes)
4. Click "Generate Podcast"
5. Wait for processing (audio will generate in background)
6. Play or download the generated podcast

### 3. Using the Chat Assistant
1. Navigate to Chat page
2. Type questions about:
   - Specific books
   - Authors
   - Literary themes
   - Podcast generation help
3. The assistant will provide contextual responses

### 4. Managing Favorites
1. Browse books in Collections
2. Click the heart icon to add/remove from favorites
3. View all favorites in the Favourites page

## ⚠️ Troubleshooting

### Common Issues

1. **Port already in use**
```bash
# Change port when running
python app.py --port=5001
```

2. **Database errors**
```bash
# Delete existing database and recreate
rm instance/educast.db
python
>>> from app import db, app
>>> with app.app_context():
>>>     db.create_all()
>>> exit()
```

3. **Missing dependencies**
```bash
# Install all required packages
pip install flask flask-sqlalchemy flask-cors flask-bcrypt pyjwt pyttsx3
```

4. **Audio generation fails**
- Ensure pyttsx3 is properly installed
- Check system audio output is working
- Verify sufficient disk space in static/audio directory

### Logs
Check the console output for detailed error messages when issues occur.

## 📄 License

This project is for educational purposes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 📧 Contact

For questions or support regarding EduCast Studio, please open an issue in the repository.

---



The README now accurately reflects a **user-focused educational platform** without any administrative capabilities.
