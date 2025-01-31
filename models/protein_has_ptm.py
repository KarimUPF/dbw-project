from app import db

class ProteinHasPTM(db.Model):
    position = db.Column(db.Integer, nullable=False)
    residue = db.Column(db.String(25), nullable=False)
    source = db.Column(db.String(45), nullable=False)
    
    #1:N relationship
    protein_accession_id = db.Column(db.String(45), db.ForeignKey('protein.accession_id'), primary_key=True)
    ptm_id = db.Column(db.Integer, db.ForeignKey('ptm.id'), primary_key=True)

    def __repr__(self):
        return f"ProteinHasPTM(Protein: '{self.protein_accession_id}', PTM: {self.ptm_id}, Position: {self.position})"