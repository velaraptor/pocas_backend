import json

from flask import Flask, render_template, redirect, flash, url_for, stream_with_context, request, Response
import os
import requests
import ast
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_login import current_user, login_user, login_required, logout_user
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_caching import Cache
from datetime import datetime
from forms import SignupForm, LoginForm, Questions, Tags, get_tags

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


@app.route('/services', methods=['GET'])
@login_required
def get_services():
    tag_form = Tags()
    services_resp = requests.get('http://pocas_api/services')
    services = services_resp.json()
    services = sorted(services['services'], key=lambda d: d['general_topic'])
    return render_template('services.html', markers=services, tags=tag_form, vals=get_tags(), active=False,
                           results=False)


@app.route('/filter', methods=['POST'])
@login_required
def filter_tags():
    if request.form['comp_select']:
        tag_form = Tags()
        f_val = request.form['comp_select']
        services_resp = requests.get('http://pocas_api/services')
        services = services_resp.json()
        services = sorted(services['services'], key=lambda d: d['general_topic'])
        services_g = list(filter(lambda x: x['general_topic'] == f_val, services))
        services_t = [x for x in services if f_val in x['tags'] and f_val != x['general_topic']]
        services = services_t + services_g

        return render_template('services.html', markers=services, tags=tag_form, vals=get_tags(), active=f_val,
                               results=False)


@app.route('/home', methods=['GET', 'POST'])
@login_required
def home_page():
    form = Questions()
    if form.validate_on_submit():
        dob = form.dob.data
        # change dob to int style
        dob = int(datetime.strftime(dob, '%m%d%Y'))
        address = form.zip_code.data
        answers = [form.question_2.data, form.question_3.data, form.question_4.data, form.question_5.data,
                   form.question_6.data, form.question_7.data, form.question_8.data, form.question_9.data,
                   form.question_10.data, form.question_11.data, form.question_12.data, form.question_13.data,
                   form.question_14.data, form.question_15.data, form.question_16.data, form.question_17.data,
                   form.question_18.data, form.question_19.data, form.question_20.data, form.question_21.data,
                   form.question_22.data, form.question_23.data, form.question_24.data,
                   form.question_25.data, form.question_26.data, form.question_27.data, form.question_28.data,
                   form.question_29.data, form.question_30.data]
        answers = list(map(int, answers))
        s = requests.Session()
        s.auth = (os.getenv('API_USER'), os.getenv('API_PASS'))
        post_questions = s.post(f"http://pocas_api/top_n?top_n=15&dob={dob}&address={address}",
                                json=answers)
        top_results = post_questions.json()
        tag_form = Tags()

        return render_template('services.html', markers=top_results['services'], tags=tag_form, active=False,
                               vals=get_tags(), results=True)
    return render_template('home.html', form=form)


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
            user.last_login = datetime.now()
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


@app.route('/results', methods=['POST', 'GET'])
def get_pdf():
    services = request.form.get('services')
    services = json.loads(services)
    s1 = requests.Session()
    s1.auth = (os.getenv('API_USER'), os.getenv('API_PASS'))
    req = s1.post(f'http://pocas_api/pdf', stream=True, json=services)
    return Response(stream_with_context(req.iter_content(chunk_size=1024 * 1)),
                    content_type=req.headers['content-type']), 200

# TODO
# add oauth with google and captcha
# save to pdf or send to email results
# click on card and show on map
