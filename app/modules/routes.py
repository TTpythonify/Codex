from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from flask_dance.contrib.github import github
from .database import *


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
                logger.info("User already authorized with GitHub. Redirecting to home.")
                return redirect(url_for("main.home"))
        except Exception as e:
            logger.error(f"Error checking GitHub authorization: {e}")
    return render_template("login_page.html")


@main_routes.route("/test-oauth")
def test_oauth():
    logger.info("Accessing test OAuth route...")
    try:
        oauth_url = url_for('github.login', _external=True)
        logger.info(f"OAuth URL generated: {oauth_url}")
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
        logger.info("User not authorized, redirecting to login page.")
        return redirect(url_for("main.login_page"))

    try:
        resp = github.get("/user")
        if not resp.ok:
            raise Exception("Failed to fetch user data from GitHub")
        user_data = resp.json()
        logger.info(f"GitHub user data fetched: {user_data.get('login')}")
        session["username"] = user_data['login']

        existing_user = user_collection.find_one({"id": user_data['id']})
        if existing_user:
            logger.info(f"Existing user found: {user_data['login']}. Updating info...")
            user_collection.update_one(
                {"id": user_data['id']},
                {"$set": {
                    "username": user_data['login'],
                    "html_url": user_data['html_url'],
                    "avatar_url": user_data['avatar_url']
                }}
            )
            user_doc = existing_user
        else:
            logger.info(f"Creating new user in MongoDB: {user_data['login']}")
            insert_result = user_collection.insert_one({
                "id": user_data['id'],
                "username": user_data['login'],
                "html_url": user_data['html_url'],
                "avatar_url": user_data['avatar_url'],
                "repos": []
            })
            user_doc = user_collection.find_one({"_id": insert_result.inserted_id})

        logger.info(f"Rendering home page for user: {user_doc['username']}")
        return render_template("home_page.html", user=user_doc)

    except Exception as e:
        logger.error(f"Error fetching or saving user data: {e}")
        return redirect(url_for("main.login_page"))


@main_routes.route("/logout")
def logout():
    logger.info("Logging out user and clearing session...")
    session.clear()
    return redirect(url_for("main.login_page"))

@main_routes.route("/authorized")
def authorized():
    logger.info("Authorized route hit. Redirecting to home...")
    return redirect(url_for("main.home"))
