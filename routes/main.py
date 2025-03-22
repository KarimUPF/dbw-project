from flask import Blueprint, render_template
from flask_login import login_required, current_user
from forms.login_form import LoginForm
from forms.registration_form import RegistrationForm
from models.all_models import History

main = Blueprint('main', __name__)

@main.route('/')
def home():
    login_form = LoginForm()
    signup_form = RegistrationForm()
    return render_template('index.html', title="Home", login_form=login_form, signup_form=signup_form)

@main.route('/browser')
def browser():
    return render_template('compare.html', title="Browser")


@main.route('/history')
def history():
    user = current_user
    user_history = History.query.filter_by(user_id=user.id).first()

    if not user_history:
        return render_template("history.html", username=user.username, history={'queries': []})

    # Orden por defecto: más reciente primero
    sorted_queries = sorted(user_history.queries, key=lambda q: q.date, reverse=True)

    return render_template("history.html", username=user.username, history={'queries': sorted_queries})

