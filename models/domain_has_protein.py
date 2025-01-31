from app import db

class DomainHasProtein(db.Model):
    __tablename__ = 'domain_has_protein'
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), primary_key=True)
    protein_accession_id = db.Column(db.String(45), db.ForeignKey('protein.accession_id'), primary_key=True)

    def __repr__(self):
        return f"DomainHasProtein(Domain: {self.domain_id}, Protein: '{self.protein_accession_id}')"