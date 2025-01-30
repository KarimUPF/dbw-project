from app import db

def load_protein(protein_id):
    return db.session.execute(db.select(Protein).filter_by(id=protein_id)).scalar_one()

class Protein(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sequence = db.Column(db.String(1000), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Protein('{self.name}', '{self.sequence}')"