from app import db

def load_protein(protein_id):
    return db.session.execute(db.select(Protein).filter_by(accession_id=protein_id)).scalar_one()

class Protein(db.Model):
    accession_id = db.Column(db.String(45),unique=True,primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sequence = db.Column(db.String(1000), nullable=False)
    length= db.Column(db.Integer, nullable=False)
    subcellular_location= db.Column(db.String(255), nullable=True)
    evidence= db.Column(db.Integer,nullable=True)
    database=db.Column(db.String(100), nullable=False)
    
    #Reference
    domains = db.relationship("Domain", secondary=domain_has_protein, backref="protein")
    ptms = db.relationship('PTM', secondary='protein_has_ptm', backref='proteins')
    #1:N relationship
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    organism_id = db.Column(db.Integer, db.ForeignKey('organism.id'), nullable=False)
    
    def __repr__(self):
        return f"Protein('{self.name}', '{self.sequence}')"