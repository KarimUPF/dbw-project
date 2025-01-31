from app import db

class History(db.Model):
    history_ID = db.Column(db.Integer, primary_key=True)

    #1:N relationship
    user_ID = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    query_ID = db.Column(db.Integer, db.ForeignKey('query.id'), nullable=False)

    #Reference
    query = db.relationship('Query', backref='history', lazy=True)

def load_history(history_id):
    return db.session.execute(db.select(History).filter_by(history_ID=history_id)).scalar_one()

