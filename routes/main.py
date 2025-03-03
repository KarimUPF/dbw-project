from flask import Blueprint, render_template
from flask_login import login_required
from forms.login_form import LoginForm
from forms.registration_form import RegistrationForm

main = Blueprint('main', __name__)

@main.route('/')
def home():
    login_form = LoginForm()
    signup_form = RegistrationForm()
    return render_template('index.html', title="Home", login_form=login_form, signup_form=signup_form)

@main.route('/browser')
def browser():
    return render_template('compare.html', title="Browser")



