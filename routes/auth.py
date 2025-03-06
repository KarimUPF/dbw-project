from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import bcrypt, db, mail
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from forms.registration_form import RegistrationForm
from forms.login_form import LoginForm
from forms.forgot_password_form import ForgotPasswordForm, ResetPasswordForm
from models.all_models import User
from datetime import datetime
from config import Config

auth = Blueprint('auth', __name__)

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))  # Already logged in
    
    login_form = LoginForm()
    signup_form = RegistrationForm() 
    if signup_form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(signup_form.password.data).decode('utf-8')
        user = User(username=signup_form.username.data, email=signup_form.email.data, password=hashed_password, last_login=datetime.now(), role_id=2)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('main.home', _anchor='login'))
    else:
        flash('There were errors in your form. Please check and try again.', 'danger')
        return redirect(url_for('main.home', _anchor='signup'))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))  # Already logged in

    login_form = LoginForm()
    signup_form = RegistrationForm() 
    if login_form.validate_on_submit():
        user = User.query.filter_by(username=login_form.username.data).first()
        if user and bcrypt.check_password_hash(user.password, login_form.password.data):
            login_user(user)
            flash('Login successful!', 'success')
            
            # Redirect to the next page if specified, otherwise home
            return redirect(url_for('main.home'))
        else:
            flash('Login failed. Check username and password.', 'danger')
            return redirect(url_for('main.home', _anchor='login'))

@auth.route('/logout')
@login_required  # Protect logout
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.home'))

# Token serializer for password reset
serializer = URLSafeTimedSerializer(Config.SECRET_KEY)

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = serializer.dumps(user.email, salt='password-reset-salt')
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            
            msg = Message('Password Reset Request', sender='noreply@example.com', recipients=[user.email])
            msg.body = f"To reset your password, visit the following link: {reset_url}\nIf you did not request this, simply ignore this email."
            mail.send(msg)
            
            flash('A password reset link has been sent to your email.', 'info')
        else:
            flash('No account found with that email.', 'danger')
        
        return redirect(url_for('auth.login'))
    
    return render_template('forgot_password.html', title='Forgot Password', form=form)

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset-salt', max_age=3600)  # 1 hour expiration
    except:
        flash('The reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.forgot_password'))
    
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=email).first()
        if user:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user.password = hashed_password
            db.session.commit()
            flash('Your password has been updated. You can now log in.', 'success')
            return redirect(url_for('auth.login'))
    
    return render_template('reset_password.html', title='Reset Password', form=form)
