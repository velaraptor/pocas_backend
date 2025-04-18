"""Frontend Flask"""
# pylint: disable=R0902, R0912, R0913, R0914, R0915, E1101, E0611

import os
import json
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import (
    render_template,
    redirect,
    flash,
    url_for,
    stream_with_context,
    request,
    Response,
    Blueprint,
    send_file,
)
import requests
from flask_login import (
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_bootstrap import SwitchField
from flask_mail import Message
from frontend.models.flask_models import mail  # pylint: disable=import-error
from frontend.forms import (  # pylint: disable=import-error
    SignupForm,
    LoginForm,
    EditForm,
    Questions,
    ChangePassForm,
    Tags,
    get_tags,
    SearchServices,
)  # pylint: disable=import-error
from frontend.consts import API_URL  # pylint: disable=import-error
from frontend.models.user import User  # pylint: disable=import-error
from frontend.models.flask_models import (  # pylint: disable=import-error
    db,
    login_manager,
)
from frontend.models.services import Services  # pylint: disable=import-error
from frontend.email_function import send_email  # pylint: disable=import-error
from frontend.setup_logging import logger  # pylint: disable=import-error

main_blueprint = Blueprint("main", __name__, template_folder="templates")


@main_blueprint.route("/", methods=["GET"])
def welcome():
    """Flash Page"""
    return render_template("public/flash.html")


@main_blueprint.route("/favicon.ico")
def favicon():
    """Favicon Route"""
    return send_file("static/icon.png")


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
    flash("You must be logged in to view that page.", "warning")
    return redirect(url_for("main.login_page"))


@main_blueprint.route("/base/services/", methods=["GET", "POST"])
@login_required
def service_base():
    """Filter Services by City"""
    search = SearchServices(search_city=current_user.search_city)
    if search.validate_on_submit():
        remember = search.remember.data
        if remember:
            current_user.search_city = search.search_city.data
            db.session.commit()
        return redirect(url_for("main.get_services", bypass=True))
    return render_template(
        "search_services.html", search=search, user_name=current_user.user_name
    )


@main_blueprint.route("/services/", methods=["GET", "POST"])
@main_blueprint.route("/services/<bypass>", methods=["GET", "POST"])
@login_required
def get_services(bypass=False):
    """Get all Services"""
    if not current_user.search_city and not bypass:
        return redirect(url_for("main.service_base"))
    tag = request.args.get("tag")
    search_param = request.args.get("search")
    search = SearchServices(search_city=current_user.search_city)

    tag_form = Tags()
    logger.debug(tag_form.tags.data)
    data = {}
    if tag:
        data["tag"] = tag
    if current_user.search_city:
        data["city"] = current_user.search_city
    if search_param:
        data["text"] = search_param
    print(data)
    services_resp = requests.get(f"{API_URL}services", timeout=20, params=data)
    payload = services_resp.json()
    obj = Services(payload)
    obj.sort()
    obj.encode_services()
    if tag:
        obj.filter(filter_val=tag)
        return render_template(
            "services.html",
            payload=obj.export(),
            tags=tag_form,
            vals=get_tags(),
            active=tag,
            results=False,
            affiliation=current_user.affiliation,
            user_name=current_user.user_name,
            search=search,
            search_value=search_param,
        )
    return render_template(
        "services.html",
        payload=obj.export(),
        tags=tag_form,
        vals=get_tags(),
        active=False,
        results=False,
        affiliation=current_user.affiliation,
        user_name=current_user.user_name,
        search=search,
        search_value=search_param,
    )


@main_blueprint.route("/filter", methods=["POST"])
@login_required
def filter_tags():
    """Filter by Tag and show services"""
    s_val = None
    f_val = None
    if request.form.get("search-value"):
        s_val = request.form["search-value"]
    if request.form.get("comp_select"):
        f_val = request.form["comp_select"]
    return redirect(url_for("main.get_services", tag=f_val, search=s_val))


@main_blueprint.route("/home", methods=["GET", "POST"])
@login_required
def home_page():
    """Home Page with Questions"""
    questions = requests.get(f"{API_URL}questions", timeout=3).json()

    for q in questions["items"]:
        setattr(Questions, "question_" + str(q["id"]), SwitchField(q["question"]))
    form = Questions()

    if form.validate_on_submit():
        age = form.age.data
        # convert to date
        dob = datetime.now() - timedelta(days=1) - relativedelta(years=age)
        # change dob to int style
        dob = int(datetime.strftime(dob, "%m%d%Y"))
        address = form.zip_code.data
        answers = [
            getattr(form, "question_" + str(question.get("id"))).data
            for question in questions["items"]
        ]
        answers = list(map(int, answers))
        s = requests.Session()
        s.auth = (os.getenv("API_USER"), os.getenv("API_PASS"))

        post_radius_check = s.post(f"{API_URL}radius_check?address={address}")
        radius_check = post_radius_check.json()
        post_questions = s.post(
            f"{API_URL}top_n?top_n=15&dob={dob}&address={address}&user_name={current_user.user_name}",
            json=answers,
        )
        payload = post_questions.json()
        logger.debug(len(payload["services"]))
        if not radius_check["radius_status"]:
            flash(
                "Patient not within 200 miles of any services in MHP Database!",
                "warning",
            )
            payload["services"] = []
        tag_form = Tags()

        obj = Services(payload)
        obj.sort("pocas_score", desc=True)
        obj.encode_services()

        return render_template(
            "services.html",
            payload=obj.export(),
            tags=tag_form,
            active=False,
            vals=get_tags(),
            results=True,
            affiliation=current_user.affiliation,
            user_name=current_user.user_name,
        )
    # get unique questions
    question_tags = []
    for question in questions["items"]:
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
        for question in questions["items"]:
            if question["main_tag"] == question_tag:
                form_question_temp = getattr(
                    form, "question_" + str(question.get("id"))
                )
                payload["questions"].append(form_question_temp)
        questions_payload.append(payload)

    return render_template(
        "home.html",
        form=form,
        questions=questions_payload,
        user_name=current_user.user_name,
    )


@main_blueprint.route("/login_page", methods=["GET", "POST"])
def login_page():
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
        flash("Invalid username/password combination", "warning")
        return redirect(url_for("main.login_page"))
    return render_template("public/login.html", form=form)


@main_blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Login Route"""
    google_key = os.getenv("GOOGLE_API_KEY")
    if current_user.is_authenticated:
        return redirect(url_for("main.home_page"))
    form = LoginForm()
    register_form = SignupForm(prefix="a")
    if register_form.validate_on_submit():
        existing_user = User.query.filter_by(
            user_name=register_form.user_name2.data.lower()
        ).first()
        if existing_user is None:
            user = User(
                user_name=register_form.user_name2.data,
                city=register_form.city.data,
                email=register_form.email.data,
                affiliation=register_form.affiliation.data,
                created_on=datetime.now(),
            )
            user.set_password(register_form.password2.data)
            db.session.add(user)
            db.session.commit()  # Create new user
            login_user(user)  # Log in as newly created user
            return redirect(url_for("main.login_page"))
        flash("A user already exists with that username.", "warning")

    if form.validate_on_submit():
        user = User.query.filter_by(user_name=form.user_name.data.lower()).first()
        if user and user.check_password(password=form.password.data):
            remember = form.remember.data
            login_user(user, remember=remember)
            user.last_login = datetime.now()
            db.session.commit()
            return redirect(url_for("main.home_page"))
        flash("Invalid username/password combination", "warning")
        return redirect(url_for("main.login_page"))
    return render_template(
        "public/index.html",
        form=form,
        googleAPIKey=google_key,
        register_form=register_form,
    )


@main_blueprint.route("/password_change", methods=["GET", "POST"])
@login_required
def change_password():
    """Change Password"""
    pass_form = ChangePassForm()
    user_name = current_user.user_name
    if pass_form.validate_on_submit():
        user = User.query.filter_by(user_name=user_name.lower()).first()
        if user.check_password(pass_form.old_password.data):
            user.set_password(pass_form.password.data)
            flash("Password Changed!", "info")
            return render_template(
                "password_change.html", form=pass_form, user_name=current_user.user_name
            )
        flash("Current Password is incorrect!", "warning")
    return render_template(
        "password_change.html", form=pass_form, user_name=current_user.user_name
    )


@main_blueprint.route("/account", methods=["GET", "POST"])
@login_required
def user_account():
    """
    User Account, change city or affiliation
    """
    form = EditForm(
        city=current_user.city,
        affiliation=current_user.affiliation,
        email=current_user.email,
        search_city=current_user.search_city,
    )
    city = current_user.city
    affiliation = current_user.affiliation
    user_name = current_user.user_name
    user_data = {"city": city, "affiliation": affiliation, "user_name": user_name}
    if form.validate_on_submit():
        existing_user = User.query.filter_by(user_name=user_name.lower()).first()
        existing_user.city = form.city.data
        existing_user.affiliation = form.affiliation.data
        existing_user.email = form.email.data
        existing_user.search_city = form.search_city.data
        db.session.commit()
        flash("Updated Profile!", "info")
        return render_template(
            "user_account.html",
            form=form,
            user_data=user_data,
            user_name=current_user.user_name,
        )
    return render_template(
        "user_account.html",
        form=form,
        user_data=user_data,
        user_name=current_user.user_name,
    )


@main_blueprint.route("/register", methods=["GET", "POST"])
def register():
    """Register Route"""
    form = SignupForm()
    google_key = os.getenv("GOOGLE_API_KEY")
    if form.validate_on_submit():
        existing_user = User.query.filter_by(
            user_name=form.user_name2.data.lower()
        ).first()
        if existing_user is None:
            user = User(
                user_name=form.user_name2.data,
                city=form.city.data,
                email=form.email.data,
                affiliation=form.affiliation.data,
                created_on=datetime.now(),
            )
            user.set_password(form.password2.data)
            db.session.add(user)
            db.session.commit()  # Create new user
            login_user(user)  # Log in as newly created user
            return redirect(url_for("main.login_page"))
        flash("A user already exists with that username.", "warning")
    return render_template(
        "public_user/register.html", form=form, googleAPIKey=google_key
    )


@main_blueprint.route("/password_reset", methods=["GET", "POST"])
def reset():
    """Reset Password email if Email is valid in db"""
    if request.method == "POST":
        email = request.form.get("email")
        user = User.verify_email(email)
        if user:
            send_email(user)
            flash("Found Email! Check your email for link to reset password!", "info")
            return redirect(url_for("main.login_page"))
        flash("No Email Found!", "warning")
    return render_template("public_user/reset.html")


@main_blueprint.route("/about", methods=["GET"])
def get_about():
    """Get About Page"""
    return render_template("public/about.html")


@main_blueprint.route("/password_reset_verified/<token>", methods=["GET", "POST"])
def reset_verified(token):
    """Reset Verified based on JWT token"""
    user = User.verify_reset_token(token)
    if not user:
        flash("no user found", "warning")
        return redirect(url_for("main.login"))

    password = request.form.get("password")
    if password:
        user.set_password(password)
        db.session.commit()
        return redirect(url_for("main.login"))

    return render_template("public_user/reset_verfied.html")


@main_blueprint.route("/results/topn/<topn_id>/<service_id>", methods=["DELETE"])
@login_required
def delete_service_topn(topn_id, service_id):
    """Delete Service for Top N result"""
    s1 = requests.Session()
    s1.auth = (os.getenv("API_USER"), os.getenv("API_PASS"))
    req = s1.delete(f"{API_URL}top_n/service/{topn_id}/{service_id}")
    return req.json()


@main_blueprint.route("/results", methods=["POST", "GET"])
@login_required
def get_pdf():
    """Get PDF from POCAS API"""
    services = request.form.get("services")
    services = json.loads(services)
    s1 = requests.Session()
    s1.auth = (os.getenv("API_USER"), os.getenv("API_PASS"))
    req = s1.post(f"{API_URL}pdf", stream=True, json=services)
    return (
        Response(
            stream_with_context(req.iter_content(chunk_size=512 * 4)),
            content_type=req.headers["content-type"],
        ),
        200,
    )


@main_blueprint.route("/email/send", methods=["POST"])
@login_required
def send_email_pdf():
    """Send an email with attached PDF"""
    email = request.form.get("recipient")
    name = request.form.get("provider")
    services = request.form.get("services")
    msg = Message()
    msg.subject = "MHP Portal Services"
    msg.sender = os.getenv("MAIL_USERNAME")
    msg.recipients = [email]

    services = json.loads(services)
    s1 = requests.Session()
    s1.auth = (os.getenv("API_USER"), os.getenv("API_PASS"))
    req = s1.post(f"{API_URL}pdf", stream=True, json=services)

    msg.attach("mhp.pdf", "application/pdf", req.content)
    msg.html = render_template("send_email.html", name=name, services=services[:5])
    mail.send(msg)
    return {"status": True}
