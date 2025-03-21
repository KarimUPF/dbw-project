from app import db, login_manager
from flask_login import UserMixin
from sqlalchemy import Enum, BLOB, JSON, Text
from datetime import datetime
from enum import Enum as PyEnum

# Define Enum for Roles
class RoleType(PyEnum):
    ADMIN = 'admin'
    USER = 'user'

# Many-to-Many Association Tables
class ProteinHasPTM(db.Model):
    __tablename__ = 'protein_has_ptm'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    position = db.Column(db.Integer, nullable=False)
    residue = db.Column(db.String(25), nullable=False)
    source = db.Column(db.String(45), nullable=False)
    protein_accession_id = db.Column(db.String(45), db.ForeignKey('protein.accession_id'), nullable=False)
    ptm_id = db.Column(db.Integer, db.ForeignKey('ptm.id'), nullable=False)

    def __repr__(self):
        return f"ProteinHasPTM(Protein: '{self.protein_accession_id}', PTM: {self.ptm_id}, Position: {self.position})"


class DomainHasProtein(db.Model):
    __tablename__ = 'domain_has_protein'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    domain_id = db.Column(db.Integer, db.ForeignKey('domain.id'), nullable=False)
    protein_accession_id = db.Column(db.String(45), db.ForeignKey('protein.accession_id'), nullable=False)

    def __repr__(self):
        return f"DomainHasProtein(Domain: {self.domain_id}, Protein: '{self.protein_accession_id}')"

# Core Models
class Protein(db.Model):
    accession_id = db.Column(db.String(45), primary_key=True, unique=True)
    name = db.Column(db.String(100), nullable=False)
    sequence = db.Column(db.Text, nullable=False)
    length = db.Column(db.Integer, nullable=False)
    subcellular_location = db.Column(db.String(255), nullable=True)
    evidence = db.Column(db.Integer, nullable=True)
    database = db.Column(db.String(100), nullable=False)
    organism_id = db.Column(db.Integer, db.ForeignKey('organism.id'), nullable=False)

    # Relationships
    domains = db.relationship("Domain", secondary="domain_has_protein", backref="proteins", lazy='select')
    ptms = db.relationship("PTM", secondary="protein_has_ptm", back_populates="proteins", lazy='select')

    def __repr__(self):
        return f"Protein('{self.name}', '{self.sequence}')"


class PTM(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    type = db.Column(db.Text, nullable=False)

    # Relationships
    proteins = db.relationship("Protein", secondary="protein_has_ptm", back_populates="ptms", lazy='select')

    def __repr__(self):
        return f"PTM('{self.type}')"


class Domain(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    accession_id = db.Column(db.String(45), nullable=False)
    name = db.Column(db.Text, nullable=False)
    position_start = db.Column(db.Integer, nullable=False)
    position_end = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"Domain('{self.name}', Start: {self.position_start}, End: {self.position_end})"


class Organism(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    accession_id = db.Column(db.String(45), nullable=False, unique=True)
    scientific_name = db.Column(db.Text, nullable=False)
    common_name = db.Column(db.String(100), nullable=True)

    # Relationships
    proteins = db.relationship('Protein', backref='organism', lazy='select')

    def __repr__(self):
        return f"Organism('{self.scientific_name}', '{self.common_name}')"


# History and Queries
class History(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    queries = db.relationship('Query', backref='history', lazy='select')

    def __repr__(self):
        return f"History(User: {self.user_id}, Queries: {len(self.queries)})"


class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    parameters = db.Column(JSON)
    summary_table = db.Column(BLOB, nullable=True)
    graph = db.Column(db.String(500), nullable=True)  # ✅ Corrige el problema
    date = db.Column(db.DateTime, default=datetime.now(), nullable=False)
    history_id = db.Column(db.Integer, db.ForeignKey('history.id'))

    # Many-to-Many with Proteins
    proteins = db.relationship('Protein', secondary='query_has_protein', backref='queries', lazy='select')

    def __repr__(self):
        return f"Query('{self.parameters}', Date: {self.date})"


class QueryHasProtein(db.Model):
    __tablename__ = 'query_has_protein'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'), nullable=False)
    protein_accession_id = db.Column(db.String(45), db.ForeignKey('protein.accession_id'), nullable=False)

    def __repr__(self):
        return f"QueryHasProtein(Query: {self.query_id}, Protein: '{self.protein_accession_id}')"


# User and Roles
class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(Enum(RoleType), nullable=False)
    users = db.relationship('User', backref='role', lazy='select')

    def __repr__(self):
        return f"Role('{self.role_name}')"


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    history = db.relationship('History', backref='user', lazy='select')

    def __repr__(self):
        return f"User('{self.username}', '{self.email}')"

# Flask-Login User Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))
