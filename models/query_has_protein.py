from app import db

class QueryHasProtein(db.Model):
    __tablename__ = 'query_has_protein'
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'), primary_key=True),
    protein_accession_id = db.Column(db.String(45), db.ForeignKey('protein.accession_id'), primary_key=True)

    def __repr__(self):
        return f"QueryHasProtein(Query: {self.query_id}, Protein: '{self.protein_accession_id}')"