from app import db

class Organism(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accession_id = db.Column(db.String(45), nullable=False, unique=True)
    scientific_name = db.Column(db.String(100), unique=True, nullable=False)
    common_name = db.Column(db.String(100), nullable=True)
    
    #Reference
    proteins = db.relationship('Protein', backref='organism', lazy=True)

    def __repr__(self):
        return f"Organism('{self.scientific_name}', '{self.common_name}')"