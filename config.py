import os  

class Config:  
    SECRET_KEY = os.getenv('SECRET_KEY', 'TEST_SECRET_KEY')  
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://karimhmd:popojad123@localhost/ptm_nexus'

    SQLALCHEMY_TRACK_MODIFICATIONS = False