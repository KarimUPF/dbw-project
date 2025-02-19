from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail

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
mail = Mail(app)

# Import routes AFTER initializing db to avoid circular imports
from routes.main import main
from routes.auth import auth
from routes.browser import ptm_comparator  # Import your PTM comparator

# Register Blueprints
app.register_blueprint(main)
app.register_blueprint(auth)
app.register_blueprint(ptm_comparator)  # Register PTM comparator route

with app.app_context(): 
    db.create_all()

if __name__ == "__main__":
    app.run(debug=True)

