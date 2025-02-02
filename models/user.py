from flask_login import UserMixin
from app import db, login_manager

@login_manager.user_loader
def load_user(user_id):
    return db.session.execute(db.select(User).filter_by(id=user_id)).scalar_one()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    last_login=db.Column(db.DateTime, nullable=True)
    #One role many users
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    #One user many history
    history = db.relationship('History', backref='user')


