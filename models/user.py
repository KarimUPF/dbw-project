from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    from models.user import User  # Lazy import to break circular dependency
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
