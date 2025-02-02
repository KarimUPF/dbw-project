from app import db, login_manager
from sqlalchemy import Enum

class Role(db.Model):
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), primary_key=True)
    role_name = db.Column(Enum('admin', 'user', name='status_enum'), nullable=False)

    #Reference
    users = db.relationship('User', backref='role', lazy=True)


@login_manager.user_loader
def load_role(role_id):
    return db.session.execute(db.select(Role).filter_by(role_id=role_id)).scalar_one()

