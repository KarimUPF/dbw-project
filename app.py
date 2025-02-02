from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate

# Initialize Flask app
app = Flask(__name__)
app.config.from_object('config.Config')

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = ''

# Import routes AFTER initializing db to avoid circular imports
from routes.main import main
from routes.auth import auth

app.register_blueprint(main)
app.register_blueprint(auth)

with app.app_context():
    db.create_all()
    print("Database created successfully!")


if __name__ == "__main__":
    app.run(debug=True)
