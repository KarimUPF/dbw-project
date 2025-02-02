from app import db

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    #One user many histories
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    #One history many queries
    queries = db.relationship('Query', backref='history')
    

def load_history(history_id):
    return db.session.execute(db.select(History).filter_by(id=history_id)).scalar_one()

