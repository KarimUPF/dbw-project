from app import db
from sqlalchemy import BLOB
from datetime import datetime

class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    parameters = db.Column(db.String(45), nullable=True)
    summary_Table = db.Column(BLOB, nullable=True)
    graph = db.Column(BLOB, nullable=True)
    date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    #Many query one history
    history_id = db.Column(db.Integer, db.ForeignKey('history.id'))
    #Many protein in many queries
    proteins = db.relationship('Protein', secondary='query_has_protein', backref='queries')

def load_query(query_id):
    return db.session.execute(db.select(Query).filter_by(id=query_id)).scalar_one()

