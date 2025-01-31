from app import db

class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  
    accession_id = db.Column(db.String(45), unique=True, nullable=False)  
    name = db.Column(db.String(45),nullable=False)
    position_start = db.Column(db.Integer, nullable=False)
    position_end = db.Column(db.Integer, nullable=False)


    def __repr__(self):
        return f"Domain('{self.name}', Start: {self.position_start}, End: {self.position_end})"
