from app import db
from sqlalchemy.dialects.mysql import BLOB
from datetime import datetime

class Query(db.Model):
    query_id = db.Column(db.Integer, primary_key=True)
    parameters = db.Column(db.String(45), nullable=True)
    summary_Table = db.Column(BLOB, nullable=True)
    graph = db.Column(BLOB, nullable=True)
    date = db.Column(db.DateTime, default=datetime, nullable=False)

    #1:N relationship
    History_History_ID = db.Column(db.Integer, db.ForeignKey('history.history_ID'), nullable=False)

    #Reference
    history = db.relationship('History', backref='query', lazy=True)

def load_query(query_id):
    return db.session.execute(db.select(Query).filter_by(Query_ID=query_id)).scalar_one()

