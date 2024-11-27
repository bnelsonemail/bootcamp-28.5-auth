"""Feedback Flask app."""

from flask import Flask, render_template, redirect, session, jsonify
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.exceptions import Unauthorized
from dotenv import load_dotenv
import os

from models import connect_db, db, User, Feedback
from forms import RegisterForm, LoginForm, FeedbackForm, DeleteForm

from email_validator import validate_email, EmailNotValidError

# Load environment variables from .env
load_dotenv()

app = Flask(__name__)

# Use environment variables for configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = os.getenv('SQLALCHEMY_TRACK_MODIFICATIONS')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = os.getenv('DEBUG_TB_INTERCEPT_REDIRECTS')


toolbar = DebugToolbarExtension(app)

connect_db(app)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Register a user: produce form and handle form submission."""

    if "username" in session:
        return redirect(f"/users/{session['username']}")

    form = RegisterForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        first_name = form.first_name.data
        last_name = form.last_name.data
        email = form.email.data

        user = User.register(username, password, first_name, last_name, email)

        db.session.commit()
        session['username'] = user.username

        return redirect(f"/users/{user.username}")

    else:
        return render_template("users/register.html", form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Produce login form or handle login."""

    if "username" in session:
        return redirect(f"/users/{session['username']}")

    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.authenticate(username, password)  # <User> or False
        if user:
            session['username'] = user.username
            return redirect(f"/users/{user.username}")
        else:
            form.username.errors = ["Invalid username/password."]
            return render_template("users/login.html", form=form)

    return render_template("users/login.html", form=form)


@app.route("/logout")
def logout():
    """Logout route."""

    session.pop("username")
    return redirect("/login")


@app.route("/users/<username>")
def show_user(username):
    """Example page for logged-in-users."""

    if "username" not in session or username != session['username']:
        raise Unauthorized()

    user = User.query.get(username)
    form = DeleteForm()

    return render_template("users/show.html", user=user, form=form)


@app.route("/users/<username>/delete", methods=["POST"])
def remove_user(username):
    """Remove user nad redirect to login."""

    if "username" not in session or username != session['username']:
        raise Unauthorized()

    user = User.query.get(username)
    db.session.delete(user)
    db.session.commit()
    session.pop("username")

    return redirect("/login")


@app.route("/users/<username>/feedback/new", methods=["GET", "POST"])
def new_feedback(username):
    """Show add-feedback form and process it."""

    if "username" not in session or username != session['username']:
        raise Unauthorized()

    form = FeedbackForm()

    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data

        feedback = Feedback(
            title=title,
            content=content,
            username=username,
        )

        db.session.add(feedback)
        db.session.commit()

        return redirect(f"/users/{feedback.username}")

    else:
        return render_template("feedback/new.html", form=form)


@app.route("/feedback/<int:feedback_id>/update", methods=["GET", "POST"])
def update_feedback(feedback_id):
    """Show update-feedback form and process it."""

    feedback = Feedback.query.get(feedback_id)

    if "username" not in session or feedback.username != session['username']:
        raise Unauthorized()

    form = FeedbackForm(obj=feedback)

    if form.validate_on_submit():
        feedback.title = form.title.data
        feedback.content = form.content.data

        db.session.commit()

        return redirect(f"/users/{feedback.username}")

    return render_template("/feedback/edit.html", form=form, feedback=feedback)


@app.route("/feedback/<int:feedback_id>/delete", methods=["POST"])
def delete_feedback(feedback_id):
    """Delete feedback."""

    feedback = Feedback.query.get(feedback_id)
    if "username" not in session or feedback.username != session['username']:
        raise Unauthorized()

    form = DeleteForm()

    if form.validate_on_submit():
        db.session.delete(feedback)
        db.session.commit()

    return redirect(f"/users/{feedback.username}")


@app.route('/validate_email', methods=['POST'])
def validate_email_route():
    try:
        data = request.get_json()
        if not data or 'email' not in data:
            return jsonify({"error": "Request must include 'email' key in JSON body"}), 400

        email = data['email']
        if not email:
            return jsonify({"error": "Email is required"}), 400

        # Validate the email
        valid = validate_email(email)
        return jsonify({"email": valid.email, "status": "Valid"}), 200

    except EmailNotValidError as e:
        return jsonify({"email": data.get('email'), "status": "Invalid", "error": str(e)}), 400

    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


@app.route("/feedback", methods=["GET"])
def list_all_feedback():
    """Display all feedback entries."""

    # Query all feedback entries from the database
    feedback_list = Feedback.query.all()

    # Render a template to display the feedback entries
    return render_template("feedback/list.html", feedback=feedback_list)


@app.route("/")
def homepage():
    """Homepage of site."""
    return render_template("homepage.html")


if __name__ == '__main__':
    app.run(debug=True)
