from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from flask_dance.contrib.github import github
from .database import *
import logging
import requests
import subprocess, tempfile, os, uuid

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


@main_routes.route("/create_repo", methods=["POST"])
def create_repo():
    logger.info("Creating a new GitHub repository...")
    if not github.authorized:
        logger.error("User not authenticated with GitHub")
        return jsonify({"message": "User not authenticated with GitHub"}), 401

    token = github.token.get("access_token") if github.token else None
    if not token:
        logger.error("Invalid GitHub token")
        return jsonify({"message": "Invalid GitHub token"}), 401

    data = request.get_json()
    name = data.get("name")
    description = data.get("description", "")
    private = data.get("private", False)

    if not name:
        logger.error("Repository name not provided")
        return jsonify({"message": "Repository name is required"}), 400

    try:
        user_resp = github.get("/user")
        if not user_resp.ok:
            raise Exception("Failed to fetch GitHub user details")
        user_data = user_resp.json()
        username = user_data["login"]

        existing_user = user_collection.find_one({"username": username})
        if existing_user:
            existing_repos = existing_user.get("repos", [])
            for repo in existing_repos:
                if repo["name"].lower() == name.lower():
                    logger.warning(f"Repository '{name}' already exists for user '{username}'")
                    return jsonify({"message": f"Repository '{name}' already exists for this user"}), 409

        logger.info(f"Creating repository on GitHub: {name}")
        
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        payload = {"name": name, "description": description, "private": private}
        response = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)
        logger.info(f"GitHub API response status: {response.status_code}")

        if response.status_code == 201:
            repo_data = response.json()
            repo_doc = {
                "id": repo_data["id"],
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "html_url": repo_data["html_url"],
                "description": repo_data.get("description"),
                "private": repo_data["private"],
                "members": [],
                "created_at": repo_data["created_at"]
            }
            user_collection.update_one({"username": username}, {"$push": {"repos": repo_doc}})
            logger.info(f"✅ Repository '{name}' added to MongoDB for user '{username}'")
            
        else:
            logger.error(f"❌ Failed to create repository: {response.json()}")
            return jsonify({"message": "Failed to create repository", "details": response.json()}), response.status_code

    except Exception as e:
        logger.error(f"Exception during repository creation: {e}")
        return jsonify({"message": "Error creating repository", "error": str(e)}), 500
    


# -----------------------------
# Repository page
# -----------------------------
@main_routes.route("/repo/<int:repo_id>")
def repo_page(repo_id):
    logger.info(f"Accessing repository page for repo ID: {repo_id}")
    if not github.authorized:
        logger.info("User not authorized, redirecting to login page.")
        return redirect(url_for("main.login_page"))

    try:
        # Get user data
        resp = github.get("/user")
        if not resp.ok:
            raise Exception("Failed to fetch user data from GitHub")
        user_data = resp.json()
        username = user_data['login']

        # Find the repository in the user's repos
        user_doc = user_collection.find_one({"username": username})
        if not user_doc:
            logger.error(f"User {username} not found in database")
            return redirect(url_for("main.home"))

        repo = None
        for r in user_doc.get("repos", []):
            if r["id"] == repo_id:
                repo = r
                break

        if not repo:
            logger.error(f"Repository with ID {repo_id} not found for user {username}")
            return redirect(url_for("main.home"))

        logger.info(f"Rendering repository page for: {repo['name']}")
        return render_template("code_editor.html", repo=repo, user=user_doc)

    except Exception as e:
        logger.error(f"Error accessing repository page: {e}")
        return redirect(url_for("main.home"))





@main_routes.route("/run_code", methods=["POST"])
def run_code():
    logger.info("Code execution requested")

    # Get code from frontend
    data = request.get_json()
    code = data.get("code", "")
    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    try:
        # Send code to sandbox service
        sandbox_url = "http://sandbox:8000/run"  # service name in docker-compose
        response = requests.post(sandbox_url, json={"code": code}, timeout=10)
        response.raise_for_status()
        result = response.json().get("output", "")

    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending code to sandbox: {e}")
        result = f"Error: Could not execute code. {str(e)}"

    # Return output or error to frontend
    return jsonify({"output": result})

    