from app import app, db, bcrypt
from models.user import User

with app.app_context():
    hashed_password = bcrypt.generate_password_hash("password").decode('utf-8')
    test_user = User(username="testuser", email="test@example.com", password=hashed_password)
    db.session.add(test_user)
    db.session.commit()
    print("Test user created successfully!")
