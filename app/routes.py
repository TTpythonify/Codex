from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from flask_dance.contrib.github import github
from .database import *
import requests

main_routes = Blueprint("main", __name__)


# -----------------------------
# Home / login page
# -----------------------------
@main_routes.route("/")
def login_page():
    if github.authorized:
        try:
            resp = github.get("/user")
            if resp.ok:
                return redirect(url_for("main.home"))
        except:
            pass
    return render_template("login_page.html")

# -----------------------------
# Test OAuth route
# -----------------------------
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
        return jsonify({
            "status": "error",
            "error": str(e)
        })

# -----------------------------
# Home page after login
# -----------------------------
@main_routes.route("/home")
def home():
    if not github.authorized:
        return redirect(url_for("main.login_page"))

    try:
        # Fetch user info from GitHub
        resp = github.get("/user")
        if not resp.ok:
            raise Exception("Failed to fetch user data from GitHub")

        user_data = resp.json()
        session["username"] = user_data['login']

        # Check if user already exists in MongoDB
        existing_user = user_collection.find_one({"id": user_data['id']})

        if existing_user:
            # Optional: update user info if it has changed
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
            # Insert new user
            insert_result = user_collection.insert_one({
                "id": user_data['id'],
                "username": user_data['login'],
                "html_url": user_data['html_url'],
                "avatar_url": user_data['avatar_url'],
                "repos": []
            })
            # Fetch the newly inserted document
            user_doc = user_collection.find_one({"_id": insert_result.inserted_id})
        print(f"\n{user_doc}\n")
        # Render the home page, passing user info to the template
        return render_template("home_page.html", user=user_doc)

    except Exception as e:
        print(f"Error fetching or saving user data: {e}")
        # Optionally log the error

    # If anything fails, redirect to login
    return redirect(url_for("main.login_page"))



@main_routes.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login_page"))

@main_routes.route("/authorized")
def authorized():
    return redirect(url_for("main.home"))


@main_routes.route("/create_repo", methods=["POST"])
def create_repo():
    if not github.authorized:
        return jsonify({"message": "User not authenticated with GitHub"}), 401

    # Safely get GitHub token
    token = github.token.get("access_token") if github.token else None
    if not token:
        return jsonify({"message": "Invalid GitHub token"}), 401

    data = request.get_json()
    name = data.get("name")
    description = data.get("description", "")
    private = data.get("private", False)

    if not name:
        return jsonify({"message": "Repository name is required"}), 400

    # Fetch the current GitHub user
    user_resp = github.get("/user")
    if not user_resp.ok:
        return jsonify({"message": "Failed to fetch GitHub user details"}), 400

    user_data = user_resp.json()
    username = user_data["login"]

    # Check if this repo name already exists for this user in MongoDB
    existing_user = user_collection.find_one({"username": username})
    if existing_user:
        existing_repos = existing_user.get("repos", [])
        for repo in existing_repos:
            if repo["name"].lower() == name.lower():
                return jsonify({"message": f"Repository '{name}' already exists for this user"}), 409

    # Create repo on GitHub
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "name": name,
        "description": description,
        "private": private
    }

    url = "https://api.github.com/user/repos"
    response = requests.post(url, headers=headers, json=payload)
    print(f"GitHub API Response: {response.json()}\n\n")

    if response.status_code == 201:
        repo_data = response.json()

        # Minimal repo data to store
        repo_doc = {
            "id": repo_data["id"],
            "name": repo_data["name"],
            "full_name": repo_data["full_name"],
            "html_url": repo_data["html_url"],
            "description": repo_data.get("description"),
            "private": repo_data["private"],
            "members":[],
            "created_at": repo_data["created_at"]
        }

        # Push new repo to user's repos list
        user_collection.update_one(
            {"username": username},
            {"$push": {"repos": repo_doc}}
        )

        print(f"✅ Added repo '{repo_data['name']}' to user '{username}' in MongoDB")

        return jsonify({
            "message": "Repository created successfully!",
            "repo": repo_doc
        }), 201

    else:
        print(f"❌ Failed to create repository: {response.json()}")
        return jsonify({
            "message": "Failed to create repository",
            "details": response.json()
        }), response.status_code
