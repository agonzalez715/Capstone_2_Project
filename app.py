import os  # Provides access to operating system functionality, like environment variables
from flask import Flask, render_template, request, redirect, url_for  # Flask essentials for routes and templating
from flask_sqlalchemy import SQLAlchemy  # ORM to interact with PostgreSQL
from flask_bcrypt import Bcrypt  # Library for password hashing
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required,
    current_user
)  # For managing user sessions
import requests  # To make HTTP requests to the OMDb API

# Optionally, load variables from the .env file
# from dotenv import load_dotenv
# load_dotenv()

# Initialize the Flask application
app = Flask(__name__)

# Configure the SQLAlchemy database URI. Ensure this matches the database you created.
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/movie_reviews'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # Disables a feature that adds overhead
# Set the secret key for session management, taken from the .env file or a fallback value
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'fallback-secret-key')

# Initialize extensions
db = SQLAlchemy(app)  # Database connection
bcrypt = Bcrypt(app)  # Password hashing

# Configure Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'login'  # Redirects unauthorized users to the login page

# Retrieve the OMDb API key from the environment variables
OMDB_API_KEY = os.getenv('OMDB_API_KEY', 'fallback-api-key')


######################
#      MODELS        #
######################

class User(db.Model, UserMixin):
    """
    Model representing a user.
    UserMixin provides default implementations for Flask-Login.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)  # Unique ID for the user
    username = db.Column(db.String(80), unique=True, nullable=False)  # Unique username
    password = db.Column(db.String(200), nullable=False)  # Hashed password

class Review(db.Model):
    """
    Model representing a review for a movie.
    """
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    movie_title = db.Column(db.String(255), nullable=False)  # Title of the movie
    review_text = db.Column(db.Text, nullable=False)  # Text of the review
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # ID of the user who wrote the review

    # Establish relationship with the User model to easily access user details
    user = db.relationship('User', backref='reviews')


######################
#   LOGIN HANDLERS   #
######################

@login_manager.user_loader
def load_user(user_id):
    """
    Flask-Login user loader callback.
    Retrieves a user by their unique ID.
    """
    return User.query.get(int(user_id))


######################
#       ROUTES       #
######################

@app.route('/')
def home():
    """
    Home page route.
    Displays a welcome message and, if logged in, a movie search form.
    """
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """
    Route for user registration.
    GET: Show registration form.
    POST: Process form data, create a new user with a hashed password, and log them in.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            # In a full app, you'd provide an error message here
            return redirect(url_for('register'))

        # Hash the password before storing it
        hashed_pw = bcrypt.generate_password_hash(password).decode('utf-8')

        # Create and save the new user
        new_user = User(username=username, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()

        # Log in the new user
        login_user(new_user)
        return redirect(url_for('home'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    Route for user login.
    GET: Show login form.
    POST: Verify credentials and log the user in.
    """
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Find the user by username
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            # Redirect back to login if credentials are invalid
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """
    Route to log the user out.
    """
    logout_user()
    return redirect(url_for('home'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    """
    Route to search for movies using the OMDb API.
    GET: Show the search form.
    POST: Process the search form, call the OMDb API, and display the movie data.
    """
    movie_data = None

    if request.method == 'POST':
        title = request.form.get('title')
        # Build the API request URL with the provided title and API key
        url = f'http://www.omdbapi.com/?apikey={OMDB_API_KEY}&t={title}'
        response = requests.get(url)
        if response.status_code == 200:
            movie_data = response.json()  # Convert the API response to a Python dictionary

    return render_template('search.html', movie=movie_data)

@app.route('/review/<title>', methods=['GET', 'POST'])
@login_required
def review(title):
    """
    Route for writing a review for a specific movie.
    GET: Show the review form.
    POST: Save the review to the database.
    """
    if request.method == 'POST':
        review_text = request.form['review_text']
        new_review = Review(
            movie_title=title,
            review_text=review_text,
            user_id=current_user.id  # Link the review to the logged-in user
        )
        db.session.add(new_review)
        db.session.commit()
        return redirect(url_for('home'))

    return render_template('review.html', title=title)

@app.route('/reviews/<title>')
def view_reviews(title):
    """
    Route to view all reviews for a given movie title.
    """
    reviews = Review.query.filter_by(movie_title=title).all()
    return render_template('reviews.html', title=title, reviews=reviews)


######################
#   MAIN EXECUTION   #
######################

if __name__ == '__main__':
    # Create all database tables (if they don't exist)
    db.create_all()
    # Start the Flask application in debug mode
    app.run(debug=True)