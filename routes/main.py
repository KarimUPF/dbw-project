from flask import Blueprint, render_template
from flask_login import login_required

main = Blueprint('main', __name__)

@main.route('/')
@login_required  # Require login for home
def home():
    return render_template('index.html', title="Home")
