from flask_login import UserMixin
from app import db, login_manager
from sqlalchemy import Enum
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Role(db.Model):
    role_ID = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(Enum('admin', 'user', name='status_enum'), nullable=False)

    #Reference
    users = db.relationship('User', backref='roles', lazy=True)


@login_manager.user_loader
def load_role(role_id):
    return db.session.execute(db.select(Role).filter_by(Role_ID=role_id)).scalar_one()

