from app import db


class PTM(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    #Reference
    protein_associations = db.relationship('ProteinHasPTM', backref='ptm', lazy=True)

    def __repr__(self):
        return f"PTM('{self.type}')"