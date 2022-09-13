from flask import Flask, render_template, redirect, flash, url_for, make_response, request, Response
import os
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user, login_user, login_required, logout_user
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_caching import Cache
import datetime
from forms import SignupForm, LoginForm

RECAPTCHA_PUBLIC_KEY = os.getenv('RECAPTCHA_PUBLIC_KEY')
RECAPTCHA_PRIVATE_KEY = os.getenv('RECAPTCHA_PRIVATE_KEY')
cache = Cache(config={'CACHE_TYPE': 'SimpleCache'})
app = Flask(__name__)
app.config.from_object(__name__)
app.config['SECRET_KEY'] = 'secret-key'
POSTGRES_URI = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}" \
               f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DBNAME')}"
app.config['SQLALCHEMY_DATABASE_URI'] = POSTGRES_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
login_manager = LoginManager()
db = SQLAlchemy(app)
login_manager.init_app(app)
cache.init_app(app)
db.create_all()


class User(UserMixin, db.Model):
    """User account model."""

    __tablename__ = 'flasklogin-users'
    id = db.Column(
        db.Integer,
        primary_key=True
    )
    user_name = db.Column(
        db.String(100),
        nullable=False,
        unique=False
    )
    password = db.Column(
        db.String(200),
        primary_key=False,
        unique=False,
        nullable=False
    )
    created_on = db.Column(
        db.DateTime,
        index=False,
        unique=False,
        nullable=True
    )
    last_login = db.Column(
        db.DateTime,
        index=False,
        unique=False,
        nullable=True
    )

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(
            password,
            method='sha256'
        )

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)


@app.route('/', methods=['GET', 'POST'])
def welcome():
    return render_template('flash.html')


@app.route("/logout")
@login_required
def logout():
    """User log-out logic."""
    logout_user()
    return redirect(url_for('login'))


@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in upon page load."""
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash('You must be logged in to view that page.')
    return redirect(url_for('login'))


@app.route('/home', methods=['GET', 'POST'])
@login_required
def home_page():
    return {'success': True}


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home_page'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(user_name=form.user_name.data.lower()).first()
        if user and user.check_password(password=form.password.data):
            remember = form.remember.data
            login_user(user, remember=remember)
            user.last_login = datetime.datetime.now()
            db.session.commit()
            return redirect(url_for('home_page'))
        flash('Invalid username/password combination')
        return redirect(url_for('login'))
    return render_template('index.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = SignupForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(user_name=form.user_name.data.lower()).first()
        if existing_user is None:
            user = User(
                user_name=form.user_name.data
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()  # Create new user
            login_user(user)  # Log in as newly created user
            return redirect(url_for('login'))
        flash('A user already exists with that username.')
    return render_template('register.html', form=form)

# TODO: https://medium.com/geekculture/how-to-make-a-web-map-with-pythons-flask-and-leaflet-9318c73c67c3

# TODO: add questionaire and hit api
# return results
# show all of them
# add oauth with google and captcha
# save to pdf or send to email results
# filter by tags
