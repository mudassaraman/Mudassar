from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from azure.storage.blob import BlobServiceClient, ContentSettings
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'f1340841002453968837b6053f9dc3fdc7fd3b7d86b87dca'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://Mudassar:Hacker%40123@mudassarimagesharing.database.windows.net/imagesharingdb?driver=ODBC+Driver+17+for+SQL+Server'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

AZURE_CONNECTION_STRING = 'DefaultEndpointsProtocol=https;AccountName=imagessharing;AccountKey=0l27ZBkdyCDfJwS06/k1/tVqXjlccQM5iVZlOrhvuy8hYEygOV+i+bpy0St3pd2dSfXSNGZ0amRW+AStCzSKag==;EndpointSuffix=core.windows.net'
AZURE_CONTAINER_NAME = 'data'

db = SQLAlchemy(app)
blob_service_client = BlobServiceClient.from_connection_string(AZURE_CONNECTION_STRING)
try:
    blob_service_client.create_container(AZURE_CONTAINER_NAME)
except Exception:
    pass

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(512), nullable=False)

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    caption = db.Column(db.String(256), nullable=True)
    location = db.Column(db.String(100), nullable=True)
    people_present = db.Column(db.String(256), nullable=True)
    upload_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    file_path = db.Column(db.String(512), nullable=False)
    media_type = db.Column(db.String(20), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    comments = db.relationship('Comment', backref='media')
    ratings = db.relationship('Rating', backref='media')

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(500), nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    user = db.relationship('User', backref='comments')

class Rating(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    value = db.Column(db.Integer, nullable=False)
    date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)
    __table_args__ = (db.UniqueConstraint('user_id', 'media_id', name='unique_user_media_rating'),)

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    return render_template_string('''
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Inter', sans-serif;
                background: url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e') no-repeat center fixed;
                background-size: cover;
                color: #000000;
                overflow-x: hidden;
            }
            .header {
                position: sticky;
                top: 0;
                background: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(10px);
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                z-index: 1000;
            }
            .header h1 {
                font-size: 1.8rem;
                text-transform: uppercase;
                color: #000000;
            }
            .nav-links a {
                color: #000000;
                text-decoration: none;
                margin: 0 1rem;
                font-weight: 500;
                transition: color 0.3s ease, transform 0.3s ease;
            }
            .nav-links a:hover {
                color: #6200ea;
                transform: translateY(-3px);
            }
            .hero {
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }
            .hero::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.6);
                z-index: -1;
            }
            .card {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 15px;
                padding: 2rem;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                width: 100%;
                max-width: 600px;
                text-align: center;
                transform-style: preserve-3d;
                transition: transform 0.5s ease;
            }
            .card:hover {
                transform: rotateY(10deg) rotateX(5deg) translateZ(20px);
            }
            .card h1 {
                font-size: 2.5rem;
                margin-bottom: 1rem;
                color: #000000;
            }
            .card p {
                font-size: 1.2rem;
                margin-bottom: 2rem;
                color: #000000;
            }
            .btn {
                background: #6200ea;
                color: #ffffff;
                padding: 0.8rem 1.5rem;
                border: none;
                border-radius: 5px;
                text-decoration: none;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .btn:hover {
                transform: translateZ(10px);
                box-shadow: 0 5px 15px rgba(98, 0, 234, 0.4);
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .card {
                animation: fadeIn 1s ease-out;
            }
            @media (max-width: 768px) {
                .header {
                    flex-direction: column;
                    gap: 1rem;
                }
                .nav-links a {
                    margin: 0.5rem;
                }
                .card {
                    margin: 1rem;
                }
            }
        </style>
        <div class="header">
            <h1>Luminora</h1>
            <div class="nav-links">
                <a href="{{ url_for('login') }}">Login</a>
                <a href="{{ url_for('register') }}">Register</a>
            </div>
        </div>
        <div class="hero">
            <div class="card">
                <h1>Welcome to Luminora</h1>
                <p>Share and discover stunning media in a vibrant community.</p>
                <a href="{{ url_for('register') }}" class="btn">Get Started</a>
            </div>
        </div>
    ''')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)
        user = User(username=username, email=email, role=role, password=hashed_password)
        db.session.add(user)
        try:
            db.session.commit()
            flash('Account created!', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Username or email already exists.', 'danger')
    return render_template_string('''
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Inter', sans-serif;
                background: url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e') no-repeat center fixed;
                background-size: cover;
                color: #000000;
                overflow-x: hidden;
            }
            .header {
                position: sticky;
                top: 0;
                background: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(10px);
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                z-index: 1000;
            }
            .header h1 {
                font-size: 1.8rem;
                text-transform: uppercase;
                color: #000000;
            }
            .nav-links a {
                color: #000000;
                text-decoration: none;
                margin: 0 1rem;
                font-weight: 500;
                transition: color 0.3s ease, transform 0.3s ease;
            }
            .nav-links a:hover {
                color: #6200ea;
                transform: translateY(-3px);
            }
            .main-content {
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }
            .main-content::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.6);
                z-index: -1;
            }
            .card {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 15px;
                padding: 2rem;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                width: 100%;
                max-width: 400px;
                transform-style: preserve-3d;
                transition: transform 0.5s ease;
            }
            .card:hover {
                transform: rotateY(10deg) rotateX(5deg) translateZ(20px);
            }
            form {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            input, select {
                padding: 0.8rem;
                border: none;
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.8);
                color: #000000;
                font-size: 1rem;
            }
            input::placeholder {
                color: #333333;
            }
            .btn {
                background: #6200ea;
                color: #ffffff;
                padding: 0.8rem;
                border: none;
                border-radius: 5px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .btn:hover {
                transform: translateZ(10px);
                box-shadow: 0 5px 15px rgba(98, 0, 234, 0.4);
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .card {
                animation: fadeIn 1s ease-out;
            }
            .flash-messages {
                margin-bottom: 1rem;
                text-align: center;
            }
            .flash-messages .success {
                color: #006600;
            }
            .flash-messages .danger {
                color: #660000;
            }
            @media (max-width: 768px) {
                .header {
                    flex-direction: column;
                    gap: 1rem;
                }
                .card {
                    margin: 1rem;
                }
            }
        </style>
        <div class="header">
            <h1>Register</h1>
            <div class="nav-links">
                <a href="{{ url_for('login') }}">Login</a>
            </div>
        </div>
        <div class="main-content">
            <div class="card">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        <div class="flash-messages">
                            {% for category, message in messages %}
                                <p class="{{ category }}">{{ message }}</p>
                            {% endfor %}
                        </div>
                    {% endif %}
                {% endwith %}
                <form method="POST">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="email" name="email" placeholder="Email" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <select name="role" required>
                        <option value="creator">Creator</option>
                        <option value="consumer">Consumer</option>
                    </select>
                    <button type="submit" class="btn">Register</button>
                </form>
            </div>
        </div>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed.', 'danger')
    return render_template_string('''
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            body {
                font-family: 'Inter', sans-serif;
                background: url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e') no-repeat center fixed;
                background-size: cover;
                color: #000000;
                overflow-x: hidden;
            }
            .header {
                position: sticky;
                top: 0;
                background: rgba(255, 255, 255, 0.8);
                backdrop-filter: blur(10px);
                padding: 1rem 2rem;
                display: flex;
                justify-content: space-between;
                align-items: center;
                z-index: 1000;
            }
            .header h1 {
                font-size: 1.8rem;
                text-transform: uppercase;
                color: #000000;
            }
            .nav-links a {
                color: #000000;
                text-decoration: none;
                margin: 0 1rem;
                font-weight: 500;
                transition: color 0.3s ease, transform 0.3s ease;
            }
            .nav-links a:hover {
                color: #6200ea;
                transform: translateY(-3px);
            }
            .main-content {
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
            }
            .main-content::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(255, 255, 255, 0.6);
                z-index: -1;
            }
            .card {
                background: rgba(255, 255, 255, 0.9);
                border-radius: 15px;
                padding: 2rem;
                backdrop-filter: blur(10px);
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                width: 100%;
                max-width: 400px;
                transform-style: preserve-3d;
                transition: transform 0.5s ease;
            }
            .card:hover {
                transform: rotateY(10deg) rotateX(5deg) translateZ(20px);
            }
            form {
                display: flex;
                flex-direction: column;
                gap: 1rem;
            }
            input {
                padding: 0.8rem;
                border: none;
                border-radius: 5px;
                background: rgba(255, 255, 255, 0.8);
                color: #000000;
                font-size: 1rem;
            }
            input::placeholder {
                color: #333333;
            }
            .btn {
                background: #6200ea;
                color: #ffffff;
                padding: 0.8rem;
                border: none;
                border-radius: 5px;
                font-weight: 600;
                cursor: pointer;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
            }
            .btn:hover {
                transform: translateZ(10px);
                box-shadow: 0 5px 15px rgba(98, 0, 234, 0.4);
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .card {
                animation: fadeIn 1s ease-out;
            }
            .flash-messages {
                margin-bottom: 1rem;
                text-align: center;
            }
            .flash-messages .danger {
                color: #660000;
            }
            @media (max-width: 768px) {
                .header {
                    flex-direction: column;
                    gap: 1rem;
                }
                .card {
                    margin: 1rem;
                }
            }
        </style>
        <div class="header">
            <h1>Login</h1>
            <div class="nav-links">
                <a href="{{ url_for('register') }}">Register</a>
            </div>
        </div>
        <div class="main-content">
            <div class="card">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        <div class="flash-messages">
                            {% for category, message in messages %}
                                <p class="{{ category }}">{{ message }}</p>
                            {% endfor %}
                        </div>
                    {% endif %}
                {% endwith %}
                <form method="POST">
                    <input type="text" name="username" placeholder="Username" required>
                    <input type="password" name="password" placeholder="Password" required>
                    <button type="submit" class="btn">Login</button>
                </form>
            </div>
        </div>
    ''')

@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    search_query = request.form.get('search_query', '')

    media = Media.query.filter(Media.title.contains(search_query)).options(
        joinedload(Media.comments).joinedload(Comment.user),
        joinedload(Media.ratings)
    ).order_by(Media.upload_date.desc()).all()

    if session['role'] == 'creator':
        return render_template_string('''
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                body {
                    font-family: 'Inter', sans-serif;
                    background: url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e') no-repeat center fixed;
                    background-size: cover;
                    color: #000000;
                    overflow-x: hidden;
                }
                .sidebar {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 250px;
                    height: 100vh;
                    background: rgba(255, 255, 255, 0.8);
                    padding: 2rem;
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                    z-index: 1000;
                }
                .sidebar h1 {
                    font-size: 1.8rem;
                    margin-bottom: 2rem;
                    color: #000000;
                }
                .sidebar a {
                    color: #000000;
                    text-decoration: none;
                    padding: 0.8rem;
                    border-radius: 5px;
                    transition: background 0.3s ease, transform 0.3s ease;
                }
                .sidebar a:hover {
                    background: #6200ea;
                    color: #ffffff;
                    transform: translateX(10px);
                }
                .main-content {
                    margin-left: 250px;
                    min-height: 100vh;
                    padding: 2rem;
                    position: relative;
                }
                .main-content::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(255, 255, 255, 0.6);
                    z-index: -1;
                }
                .card {
                    background: rgba(255, 255, 255, 0.9);
                    border-radius: 15px;
                    padding: 2rem;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                    max-width: 600px;
                    margin: 0 auto;
                    transform-style: preserve-3d;
                    transition: transform 0.5s ease;
                }
                .card:hover {
                    transform: rotateY(10deg) rotateX(5deg) translateZ(20px);
                }
                form {
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                }
                input, select {
                    padding: 0.8rem;
                    border: none;
                    border-radius: 5px;
                    background: rgba(255, 255, 255, 0.8);
                    color: #000000;
                    font-size: 1rem;
                }
                input::placeholder {
                    color: #333333;
                }
                .btn {
                    background: #6200ea;
                    color: #ffffff;
                    padding: 0.8rem;
                    border: none;
                    border-radius: 5px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                }
                .btn:hover {
                    transform: translateZ(10px);
                    box-shadow: 0 5px 15px rgba(98, 0, 234, 0.4);
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .card {
                    animation: fadeIn 1s ease-out;
                }
                .flash-messages {
                    margin-bottom: 1rem;
                    text-align: center;
                }
                .flash-messages .success {
                    color: #006600;
                }
                @media (max-width: 768px) {
                    .sidebar {
                        width: 200px;
                    }
                    .main-content {
                        margin-left: 200px;
                    }
                    .card {
                        margin: 1rem;
                    }
                }
                @media (max-width: 576px) {
                    .sidebar {
                        width: 100%;
                        height: auto;
                        position: static;
                    }
                    .main-content {
                        margin-left: 0;
                    }
                }
            </style>
            <div class="sidebar">
                <h1>Luminora</h1>
                <a href="{{ url_for('dashboard') }}">Upload Media</a>
                <a href="{{ url_for('logout') }}">Logout</a>
            </div>
            <div class="main-content">
                <div class="card">
                    {% with messages = get_flashed_messages(with_categories=true) %}
                        {% if messages %}
                            <div class="flash-messages">
                                {% for category, message in messages %}
                                    <p class="{{ category }}">{{ message }}</p>
                                {% endfor %}
                            </div>
                        {% endif %}
                    {% endwith %}
                    <form method="POST" action="{{ url_for('upload') }}" enctype="multipart/form-data">
                        <input type="text" name="title" placeholder="Title" required>
                        <input type="text" name="caption" placeholder="Caption">
                        <input type="text" name="location" placeholder="Location">
                        <input type="text" name="people_present" placeholder="People Present">
                        <input type="file" name="file" required>
                        <select name="media_type" required>
                            <option value="video">Video</option>
                            <option value="picture">Picture</option>
                        </select>
                        <button type="submit" class="btn">Upload Media</button>
                    </form>
                </div>
            </div>
        ''')
    else:
        return render_template_string('''
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }
                body {
                    font-family: 'Inter', sans-serif;
                    background: url('https://images.unsplash.com/photo-1507525428034-b723cf961d3e') no-repeat center fixed;
                    background-size: cover;
                    color: #000000;
                    overflow-x: hidden;
                }
                .sidebar {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 250px;
                    height: 100vh;
                    background: rgba(255, 255, 255, 0.8);
                    padding: 2rem;
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                    z-index: 1000;
                }
                .sidebar h1 {
                    font-size: 1.8rem;
                    margin-bottom: 2rem;
                    color: #000000;
                }
                .sidebar a {
                    color: #000000;
                    text-decoration: none;
                    padding: 0.8rem;
                    border-radius: 5px;
                    transition: background 0.3s ease, transform 0.3s ease;
                }
                .sidebar a:hover {
                    background: #6200ea;
                    color: #ffffff;
                    transform: translateX(10px);
                }
                .main-content {
                    margin-left: 250px;
                    min-height: 100vh;
                    padding: 2rem;
                    position: relative;
                }
                .main-content::before {
                    content: '';
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(255, 255, 255, 0.6);
                    z-index: -1;
                }
                .search-form {
                    max-width: 600px;
                    margin: 0 auto 2rem;
                    display: flex;
                    gap: 1rem;
                }
                .search-form input {
                    flex: 1;
                    padding: 0.8rem;
                    border: none;
                    border-radius: 5px;
                    background: rgba(255, 255, 255, 0.8);
                    color: #000000;
                }
                .search-form .btn {
                    background: #6200ea;
                    padding: 0.8rem 1.5rem;
                    border: none;
                    border-radius: 5px;
                    color: #ffffff;
                    cursor: pointer;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                }
                .search-form .btn:hover {
                    transform: translateZ(10px);
                    box-shadow: 0 5px 15px rgba(98, 0, 234, 0.4);
                }
                .media-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                    gap: 2rem;
                }
                .media-card {
                    background: rgba(255, 255, 255, 0.9);
                    border-radius: 15px;
                    padding: 1.5rem;
                    backdrop-filter: blur(10px);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
                    transform-style: preserve-3d;
                    transition: transform 0.5s ease;
                }
                .media-card:hover {
                    transform: rotateY(10deg) rotateX(5deg) translateZ(20px);
                }
                .media-card img, .media-card video {
                    width: 100%;
                    border-radius: 10px;
                    margin-bottom: 1rem;
                }
                .media-card h2 {
                    font-size: 1.5rem;
                    margin-bottom: 0.5rem;
                    color: #000000;
                }
                .media-card p {
                    font-size: 1rem;
                    margin-bottom: 1rem;
                    color: #000000;
                }
                .comments, .ratings {
                    margin: 1rem 0;
                }
                .comments ul, .ratings ul {
                    list-style: none;
                    padding: 0;
                }
                .comments li, .ratings li {
                    margin-bottom: 0.5rem;
                    color: #000000;
                }
                form {
                    display: flex;
                    flex-direction: column;
                    gap: 1rem;
                }
                input, select {
                    padding: 0.8rem;
                    border: none;
                    border-radius: 5px;
                    background: rgba(255, 255, 255, 0.8);
                    color: #000000;
                }
                input::placeholder {
                    color: #333333;
                }
                .btn {
                    background: #6200ea;
                    color: #ffffff;
                    padding: 0.8rem;
                    border: none;
                    border-radius: 5px;
                    font-weight: 600;
                    cursor: pointer;
                    transition: transform 0.3s ease, box-shadow 0.3s ease;
                }
                .btn:hover {
                    transform: translateZ(10px);
                    box-shadow: 0 5px 15px rgba(98, 0, 234, 0.4);
                }
                @keyframes fadeIn {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .media-card {
                    animation: fadeIn 1s ease-out;
                }
                .flash-messages {
                    margin-bottom: 1rem;
                    text-align: center;
                }
                .flash-messages .success {
                    color: #006600;
                }
                .flash-messages .danger {
                    color: #660000;
                }
                .flash-messages .warning {
                    color: #666600;
                }
                @media (max-width: 768px) {
                    .sidebar {
                        width: 200px;
                    }
                    .main-content {
                        margin-left: 200px;
                    }
                    .media-grid {
                        grid-template-columns: 1fr;
                    }
                }
                @media (max-width: 576px) {
                    .sidebar {
                        width: 100%;
                        height: auto;
                        position: static;
                    }
                    .main-content {
                        margin-left: 0;
                    }
                }
            </style>
            <div class="sidebar">
                <h1>Luminora</h1>
                <a href="{{ url_for('dashboard') }}">Dashboard</a>
                <a href="{{ url_for('logout') }}">Logout</a>
            </div>
            <div class="main-content">
                {% with messages = get_flashed_messages(with_categories=true) %}
                    {% if messages %}
                        <div class="flash-messages">
                            {% for category, message in messages %}
                                <p class="{{ category }}">{{ message }}</p>
                            {% endfor %}
                        </div>
                    {% endif %}
                {% endwith %}
                <form class="search-form" method="POST" action="{{ url_for('dashboard') }}">
                    <input type="text" name="search_query" placeholder="Search by Title" value="{{ request.form.get('search_query', '') }}">
                    <button type="submit" class="btn">Search</button>
                </form>
                {% if not media %}
                    <p style="text-align: center;">No results found.</p>
                {% endif %}
                <div class="media-grid">
                    {% for item in media %}
                        <div class="media-card">
                            <h2>{{ item.title | e }}</h2>
                            <p>{{ item.caption | e }}</p>
                            {% if item.media_type == 'video' %}
                                <video width="100%" controls>
                                    <source src="{{ item.file_path | e }}" type="video/mp4">
                                    Your browser does not support video playback.
                                </video>
                            {% else %}
                                <img src="{{ item.file_path | e }}" alt="Picture">
                            {% endif %}
                            <div class="comments">
                                <h4>Comments:</h4>
                                <ul>
                                    {% for comment in item.comments %}
                                        <li><strong>{{ comment.user.username | e }}:</strong> {{ comment.text | e }}</li>
                                    {% endfor %}
                                    {% if not item.comments %}
                                        <li>No comments yet.</li>
                                    {% endif %}
                                </ul>
                                <form method="POST" action="{{ url_for('comment') }}">
                                    <input type="hidden" name="media_id" value="{{ item.id }}">
                                    <input type="text" name="text" placeholder="Comment" required>
                                    <button type="submit" class="btn">Comment</button>
                                </form>
                            </div>
                            <div class="ratings">
                                <h4>Ratings:</h4>
                                <ul>
                                    {% for rating in item.ratings %}
                                        <li>{{ rating.value | e }}/5</li>
                                    {% endfor %}
                                    {% if not item.ratings %}
                                        <li>No ratings yet.</li>
                                    {% endif %}
                                </ul>
                                <form method="POST" action="{{ url_for('rate') }}">
                                    <input type="hidden" name="media_id" value="{{ item.id }}">
                                    <input type="number" name="value" min="1" max="5" required>
                                    <button type="submit" class="btn">Rate</button>
                                </form>
                            </div>
                        </div>
                    {% endfor %}
                </div>
            </div>
        ''', media=media)

@app.route('/upload', methods=['POST'])
def upload():
    if 'user_id' not in session or session['role'] != 'creator':
        return redirect(url_for('login'))
    title = request.form['title']
    caption = request.form['caption']
    location = request.form['location']
    people_present = request.form['people_present']
    file = request.files['file']
    media_type = request.form['media_type']
    if file:
        filename = f"{uuid.uuid4()}_{file.filename}"
        blob_client = blob_service_client.get_blob_client(container=AZURE_CONTAINER_NAME, blob=filename)
        blob_client.upload_blob(file, overwrite=True, content_settings=ContentSettings(
            content_type='video/mp4' if media_type == 'video' else 'image/jpeg'))
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{AZURE_CONTAINER_NAME}/{filename}"
        media = Media(
            title=title,
            caption=caption,
            location=location,
            people_present=people_present,
            file_path=blob_url,
            media_type=media_type if media_type in ['video', 'picture'] else 'picture',
            creator_id=session['user_id']
        )
        db.session.add(media)
        db.session.commit()
        flash('Media uploaded successfully!', 'success')
    else:
        flash('No file uploaded.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/comment', methods=['POST'])
def comment():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    comment = Comment(
        text=request.form['text'],
        user_id=session['user_id'],
        media_id=request.form['media_id']
    )
    db.session.add(comment)
    db.session.commit()
    flash('Comment added!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/rate', methods=['POST'])
def rate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    media_id = request.form.get('media_id')
    if not media_id:
        flash('Media ID is required to rate!', 'danger')
        return redirect(url_for('dashboard'))
    try:
        media_id = int(media_id)
    except ValueError:
        flash('Invalid Media ID!', 'danger')
        return redirect(url_for('dashboard'))
    media = Media.query.get(media_id)
    if not media:
        flash('Invalid media item!', 'danger')
        return redirect(url_for('dashboard'))
    existing_rating = Rating.query.filter_by(user_id=session['user_id'], media_id=media_id).first()
    if existing_rating:
        flash('You have already rated this media!', 'warning')
        return redirect(url_for('dashboard'))
    rating = Rating(
        value=int(request.form['value']),
        user_id=session['user_id'],
        media_id=media_id
    )
    db.session.add(rating)
    try:
        db.session.commit()
        flash('Media rated!', 'success')
    except IntegrityError:
        db.session.rollback()
        flash('Error submitting rating.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('role', None)
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)