from app import db, login_manager
from flask_login import UserMixin
from sqlalchemy import BLOB, Enum
from datetime import datetime



class DomainHasProtein(db.Model):
    __tablename__ = 'domain_has_protein'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'))
    protein_accession_id = db.Column(db.String(45), db.ForeignKey('protein.accession_id'))

    def __repr__(self):
        return f"DomainHasProtein(Domain: {self.domain_id}, Protein: '{self.protein_accession_id}')"

class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)  
    accession_id = db.Column(db.String(45), nullable=False)  
    name = db.Column(db.String(45),nullable=False)
    position_start = db.Column(db.Integer, nullable=False)
    position_end = db.Column(db.Integer, nullable=False)


    def __repr__(self):
        return f"Domain('{self.name}', Start: {self.position_start}, End: {self.position_end})"

class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    #One user many histories
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    #One history many queries
    queries = db.relationship('Query', backref='history')
    

def load_history(history_id):
    return db.session.execute(db.select(History).filter_by(id=history_id)).scalar_one()

class Organism(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accession_id = db.Column(db.String(45), nullable=False, unique=True)
    scientific_name = db.Column(db.String(100), unique=True, nullable=False)
    common_name = db.Column(db.String(100), nullable=True)
    
    #One ormganism many proteins
    proteins = db.relationship('Protein', backref='organism')

    def __repr__(self):
        return f"Organism('{self.scientific_name}', '{self.common_name}')"

class ProteinHasPTM(db.Model):
    __tablename__ = 'protein_has_ptm'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    position = db.Column(db.Integer, nullable=False)
    residue = db.Column(db.String(25), nullable=False)
    source = db.Column(db.String(45), nullable=False)
    
    #Many to many
    protein_accession_id = db.Column(db.String(45), db.ForeignKey('protein.accession_id'))
    ptm_id = db.Column(db.Integer, db.ForeignKey('ptm.id'))

    def __repr__(self):
        return f"ProteinHasPTM(Protein: '{self.protein_accession_id}', PTM: {self.ptm_id}, Position: {self.position})"
        
def load_protein(protein_id):
    return db.session.execute(db.select(Protein).filter_by(accession_id=protein_id)).scalar_one()

class Protein(db.Model):
    accession_id = db.Column(db.String(45),unique=True,primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sequence = db.Column(db.Text, nullable=False)
    length= db.Column(db.Integer, nullable=False)
    subcellular_location= db.Column(db.String(255), nullable=True)
    evidence= db.Column(db.Integer,nullable=True)
    database=db.Column(db.String(100), nullable=False)
    
    #Many to many
    domains = db.relationship("Domain", secondary='domain_has_protein', backref="protein")
    ptms = db.relationship('PTM', secondary='protein_has_ptm', backref='protein')
    #1:N relationship
    organism_id = db.Column(db.Integer, db.ForeignKey('organism.id'), nullable=False)
    
    def __repr__(self):
        return f"Protein('{self.name}', '{self.sequence}')"


class PTM(db.Model):
    id = db.Column(db.Integer, unique=True, primary_key=True)
    type = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)

    #Reference
    protein_associations = db.relationship('ProteinHasPTM', backref='ptm', lazy=True)

    def __repr__(self):
        return f"PTM('{self.type}')"

class QueryHasProtein(db.Model):
    __tablename__ = 'query_has_protein'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'))
    protein_accession_id = db.Column(db.String(45), db.ForeignKey('protein.accession_id'))

    def __repr__(self):
        return f"QueryHasProtein(Query: {self.query_id}, Protein: '{self.protein_accession_id}')"

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


@login_manager.user_loader
def load_role(role_id):
    return db.session.execute(db.select(Role).filter_by(role_id=role_id)).scalar_one()

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(Enum('admin', 'user', name='status_enum'), nullable=False)
    #One role many users
    users = db.relationship('User', backref='role', lazy=True)


@login_manager.user_loader
def load_role(role_id):
    return db.session.execute(db.select(Role).filter_by(id=role_id)).scalar_one()

@login_manager.user_loader
def load_user(user_id):
    return db.session.execute(db.select(User).filter_by(id=user_id)).scalar_one()

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    last_login=db.Column(db.DateTime, nullable=True)
    #One role many users
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    #One user many history
    history = db.relationship('History', backref='user')
