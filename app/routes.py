from flask import Blueprint, render_template, redirect, url_for
from flask_dance.contrib.github import github

main_routes = Blueprint("main", __name__)

# Home / login page
@main_routes.route("/")
def login_page():
    # If user already logged in via GitHub, show username
    if github.authorized:
        resp = github.get("/user")
        username = resp.json()["login"]
        return render_template("home_page.html")
    return render_template("login_page.html")  # Show login page if not logged in
