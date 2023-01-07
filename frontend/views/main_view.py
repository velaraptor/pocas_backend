"""Frontend Flask"""
# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611

import os
import json
from datetime import datetime
from flask import (
    render_template,
    redirect,
    flash,
    url_for,
    stream_with_context,
    request,
    Response,
    Blueprint,
)
import requests
from flask_login import (
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_bootstrap import SwitchField
from frontend.forms import (  # pylint: disable=import-error
    SignupForm,
    LoginForm,
    Questions,
    Tags,
    get_tags,
)  # pylint: disable=import-error
from frontend.consts import API_URL  # pylint: disable=import-error
from frontend.models.user import User
from frontend.models.flask_models import db, login_manager

main_blueprint = Blueprint("main", __name__, template_folder="templates")


@main_blueprint.route("/", methods=["GET"])
def welcome():
    """Flash Page"""
    return render_template("flash.html")


@main_blueprint.route("/logout")
@login_required
def logout():
    """User log-out logic."""
    logout_user()
    return redirect(url_for("main.login"))


@login_manager.user_loader
def load_user(user_id):
    """Check if user is logged-in upon page load."""
    if user_id is not None:
        return User.query.get(user_id)
    return None


@login_manager.unauthorized_handler
def unauthorized():
    """Redirect unauthorized users to Login page."""
    flash("You must be logged in to view that page.")
    return redirect(url_for("main.login"))


@main_blueprint.route("/services", methods=["GET"])
@login_required
def get_services():
    """Get all Services"""
    tag_form = Tags()
    services_resp = requests.get(f"{API_URL}services", timeout=20)
    services = services_resp.json()
    services = sorted(services["services"], key=lambda d: d["general_topic"])
    return render_template(
        "services.html",
        markers=services,
        tags=tag_form,
        vals=get_tags(),
        active=False,
        results=False,
        current_user=None,
    )


@main_blueprint.route("/filter", methods=["POST"])
@login_required
def filter_tags():
    """Filter by Tag and show services"""
    if request.form["comp_select"]:
        tag_form = Tags()
        print(tag_form.tags.data)
        f_val = request.form["comp_select"]
        services_resp = requests.get(f"{API_URL}services", timeout=20)
        services = services_resp.json()
        services = sorted(services["services"], key=lambda d: d["general_topic"])
        if f_val == " ":
            return render_template(
                "services.html",
                markers=list(services),
                tags=tag_form,
                vals=get_tags(),
                active=f_val,
                results=False,
                current_user=None,
            )
        services_g = list(filter(lambda x: x["general_topic"] == f_val, services))
        services_t = [
            x for x in services if f_val in x["tags"] and f_val != x["general_topic"]
        ]
        services = services_t + services_g

        return render_template(
            "services.html",
            markers=services,
            tags=tag_form,
            vals=get_tags(),
            active=f_val,
            results=False,
            current_user=None,
        )
    return None


@main_blueprint.route("/home", methods=["GET", "POST"])
@login_required
def home_page():
    """Home Page with Questions"""
    questions = requests.get(f"{API_URL}questions", timeout=3).json()

    for q in questions["questions"]:
        setattr(Questions, "question_" + str(q["id"]), SwitchField(q["question"]))
    form = Questions()

    if form.validate_on_submit():
        dob = form.dob.data
        # change dob to int style
        dob = int(datetime.strftime(dob, "%m%d%Y"))
        address = form.zip_code.data
        answers = [
            getattr(form, "question_" + str(question.get("id"))).data
            for question in questions["questions"]
        ]
        answers = list(map(int, answers))
        s = requests.Session()
        s.auth = (os.getenv("API_USER"), os.getenv("API_PASS"))
        post_questions = s.post(
            f"{API_URL}top_n?top_n=15&dob={dob}&address={address}&user_name={current_user.user_name}",
            json=answers,
        )
        top_results = post_questions.json()
        tag_form = Tags()

        # TODO: check if location is nowhere near and emit a dimissable alert, if len is zero
        return render_template(
            "services.html",
            markers=top_results["services"],
            tags=tag_form,
            active=False,
            vals=get_tags(),
            results=True,
            current_user=top_results["user_loc"],
        )
    # get unique questions
    question_tags = []
    for question in questions["questions"]:
        question_tags.append(question["main_tag"])
    question_tags = sorted(set(question_tags))

    # make a questions list with dict in each element with main_tag, safe_html_name and all questions from form
    questions_payload = []
    for question_tag in question_tags:
        payload = {
            "name": question_tag,
            "safe_html_name": question_tag.replace(" ", ""),
            "questions": [],
        }
        for question in questions["questions"]:
            if question["main_tag"] == question_tag:
                form_question_temp = getattr(
                    form, "question_" + str(question.get("id"))
                )
                payload["questions"].append(form_question_temp)
        questions_payload.append(payload)

    return render_template("home.html", form=form, questions=questions_payload)


@main_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Login Route"""
    if current_user.is_authenticated:
        return redirect(url_for("main.home_page"))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(user_name=form.user_name.data.lower()).first()
        if user and user.check_password(password=form.password.data):
            remember = form.remember.data
            login_user(user, remember=remember)
            user.last_login = datetime.now()
            db.session.commit()
            return redirect(url_for("main.home_page"))
        flash("Invalid username/password combination")
        return redirect(url_for("main.login"))
    return render_template("index.html", form=form)


@main_blueprint.route("/register", methods=["GET", "POST"])
def register():
    """Register Route"""
    form = SignupForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(
            user_name=form.user_name.data.lower()
        ).first()
        if existing_user is None:
            user = User(
                user_name=form.user_name.data,
                city=form.city.data,
                affiliation=form.affiliation.data,
                created_on=datetime.now(),
            )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()  # Create new user
            login_user(user)  # Log in as newly created user
            return redirect(url_for("main.login"))
        flash("A user already exists with that username.")
    return render_template("register.html", form=form)


@main_blueprint.route("/results", methods=["POST", "GET"])
def get_pdf():
    """Get PDF from POCAS API"""
    services = request.form.get("services")
    services = json.loads(services)
    s1 = requests.Session()
    s1.auth = (os.getenv("API_USER"), os.getenv("API_PASS"))
    req = s1.post(f"{API_URL}pdf", stream=True, json=services)
    return (
        Response(
            stream_with_context(req.iter_content(chunk_size=1024 * 1)),
            content_type=req.headers["content-type"],
        ),
        200,
    )
