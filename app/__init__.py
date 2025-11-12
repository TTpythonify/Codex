import os
from flask import Flask
from dotenv import load_dotenv
from app.routes import main_routes
from flask_dance.contrib.github import make_github_blueprint


load_dotenv()

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_secret")

    # GitHub OAuth blueprint
    github_bp = make_github_blueprint(
        client_id=os.environ.get("GITHUB_CLIENT_ID"),
        client_secret=os.environ.get("GITHUB_CLIENT_SECRET"),
        scope="repo"
    )
    app.register_blueprint(github_bp, url_prefix="/login")

    # Register your own routes
    app.register_blueprint(main_routes)

    return app
