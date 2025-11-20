from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from flask_dance.contrib.github import github
from .database import *
import logging
import datetime




main_routes = Blueprint("main", __name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@main_routes.route("/")
def login_page():
    logger.info("Rendering login page...")
    if github.authorized:
        try:
            resp = github.get("/user")
            if resp.ok:
                return redirect(url_for("main.home"))
        except Exception as e:
            logger.error(f"Error checking GitHub authorization: {e}")
    return render_template("login_page.html")


@main_routes.route("/test-oauth")
def test_oauth():
    try:
        oauth_url = url_for('github.login', _external=True)
        return jsonify({
            "status": "success",
            "oauth_url": oauth_url,
            "message": "OAuth route exists!"
        })
    except Exception as e:
        logger.error(f"Error in test OAuth: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        })


@main_routes.route("/home")
def home():
    logger.info("Accessing home page...")
    if not github.authorized:
        return redirect(url_for("main.login_page"))

    try:
        # Fetch GitHub user data
        resp = github.get("/user")
        if not resp.ok:
            raise Exception("Failed to fetch user data from GitHub")
        user_data = resp.json()
        github_id = user_data['id']
        github_username = user_data['login']

        session["username"] = github_username

        # Look for user in DB
        existing_user = user_collection.find_one({"github_id": github_id})
        if existing_user:
            user_collection.update_one(
                {"github_id": github_id},
                {"$set": {
                    "username": github_username,
                    "html_url": user_data['html_url'],
                    "avatar_url": user_data['avatar_url'],
                    "updated_at": datetime.datetime.utcnow()
                }}
            )
            user_doc = user_collection.find_one({"github_id": github_id})
        else:
            insert_result = user_collection.insert_one({
                "github_id": github_id,
                "username": github_username,
                "html_url": user_data['html_url'],
                "avatar_url": user_data['avatar_url'],
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow()
            })
            user_doc = user_collection.find_one({"_id": insert_result.inserted_id})

        # Fetch all repositories for this user
        repos_cursor = repositories_collection.find({"user_id": user_doc["_id"]})
        repos = []
        for repo in repos_cursor:
            # Convert ObjectId and datetime for safe display in template
            repo["_id"] = str(repo["_id"])
            if isinstance(repo.get("created_at"), datetime.datetime):
                repo["created_at"] = repo["created_at"].strftime("%Y-%m-%d")
            if isinstance(repo.get("updated_at"), datetime.datetime):
                repo["updated_at"] = repo["updated_at"].strftime("%Y-%m-%d")
            repos.append(repo)

        return render_template("home_page.html", user=user_doc, repos=repos)

    except Exception as e:
        logger.error(f"Error fetching or saving user data: {e}")
        return redirect(url_for("main.login_page"))


@main_routes.route("/public_repositories")
def public_repositories():

    logger.info("Accessing home page...")
    if not github.authorized:
        return redirect(url_for("main.login_page"))

    try:
        # Fetch GitHub user data
        resp = github.get("/user")
        if not resp.ok:
            raise Exception("Failed to fetch user data from GitHub")
        user_data = resp.json()
        github_id = user_data['id']
        github_username = user_data['login']

        session["username"] = github_username

        # Look for user in DB
        existing_user = user_collection.find_one({"github_id": github_id})
        if existing_user:
            user_collection.update_one(
                {"github_id": github_id},
                {"$set": {
                    "username": github_username,
                    "html_url": user_data['html_url'],
                    "avatar_url": user_data['avatar_url'],
                    "updated_at": datetime.datetime.utcnow()
                }}
            )
            user_doc = user_collection.find_one({"github_id": github_id})

        return render_template("public_repositories.html", user=user_doc)    

    except Exception as e:
        logger.error(f"Error fetching or saving user data: {e}")
        return redirect(url_for("main.login_page"))



@main_routes.route("/activity_feed")
def activity_feed():

    logger.info("Accessing home page...")
    if not github.authorized:
        return redirect(url_for("main.login_page"))

    try:
        # Fetch GitHub user data
        resp = github.get("/user")
        if not resp.ok:
            raise Exception("Failed to fetch user data from GitHub")
        user_data = resp.json()
        github_id = user_data['id']
        github_username = user_data['login']

        session["username"] = github_username

        # Look for user in DB
        existing_user = user_collection.find_one({"github_id": github_id})
        if existing_user:
            user_collection.update_one(
                {"github_id": github_id},
                {"$set": {
                    "username": github_username,
                    "html_url": user_data['html_url'],
                    "avatar_url": user_data['avatar_url'],
                    "updated_at": datetime.datetime.utcnow()
                }}
            )
            user_doc = user_collection.find_one({"github_id": github_id})

        return render_template("activity_feed.html", user=user_doc)   
    

    except Exception as e:
        logger.error(f"Error fetching or saving user data: {e}")
        return redirect(url_for("main.login_page"))


@main_routes.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login_page"))


@main_routes.route("/authorized")
def authorized():
    return redirect(url_for("main.home"))
