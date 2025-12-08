from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from flask_dance.contrib.github import github
from .database import *
import logging
import datetime
from bson import ObjectId





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
            logger.error(f"Error checking GitHub authoriz`ation: {e}")
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

        # Store GitHub info in session
        session["username"] = github_username
        session["github_id"] = github_id

        # Check if user exists in DB
        existing_user = user_collection.find_one({"github_id": github_id})
        if existing_user:
            # Update user info
            user_collection.update_one(
                {"github_id": github_id},
                {"$set": {
                    "username": github_username,
                    "html_url": user_data.get('html_url'),
                    "avatar_url": user_data.get('avatar_url'),
                    "updated_at": datetime.datetime.utcnow()
                }}
            )
            user_doc = user_collection.find_one({"github_id": github_id})
        else:
            # Insert new user
            insert_result = user_collection.insert_one({
                "github_id": github_id,
                "username": github_username,
                "html_url": user_data.get('html_url'),
                "avatar_url": user_data.get('avatar_url'),
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow()
            })
            user_doc = user_collection.find_one({"_id": insert_result.inserted_id})

        # ✅ Fetch all repos where user is owner or member
        repos_cursor = repositories_collection.find({
            "$or": [
                {"owner_github_id": github_id},  # Owned repos
                {"members": github_id}           # Joined repos (checking GitHub ID)
            ]
        }).sort("created_at", -1)

        repos = []
        for repo in repos_cursor:
            # Flag to indicate ownership
            repo["is_owner"] = repo.get("owner_github_id") == github_id
            repo["members"] = repo.get("members", [])
            # Convert ObjectId to string
            repo["_id"] = str(repo["_id"])

            # Format dates for display
            if isinstance(repo.get("created_at"), datetime.datetime):
                repo["created_at"] = repo["created_at"].strftime("%Y-%m-%d")
            if isinstance(repo.get("updated_at"), datetime.datetime):
                repo["updated_at"] = repo["updated_at"].strftime("%Y-%m-%d")

            repos.append(repo)
        
        # Debug logging
        logger.info(f"User {github_username} (ID: {github_id}) has access to {len(repos)} repos")
        for repo in repos:
            logger.info(f"  - {repo['name']} (Owner: {repo['is_owner']}, Members: {repo['members']})")

        # Pass github_id to template
        return render_template("home_page.html", user=user_doc, repos=repos, current_github_id=github_id)

    except Exception as e:
        logger.error(f"Error fetching or saving user data: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for("main.login_page"))



@main_routes.route("/public_repositories")
def public_repositories():
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
            user_doc = user_collection.find({"_id": insert_result.inserted_id})

        repos_cursor = repositories_collection.find({
            "private": False,                # only public repos
            "user_id": {"$ne": user_doc["_id"]},  # not owned by user
            "members": {"$ne": github_id}    # user is NOT a member
        })

        repos = []

        for repo in repos_cursor:
            # Convert ObjectId and datetime for safe display in template
            repo["_id"] = str(repo["_id"])
            if isinstance(repo.get("created_at"), datetime.datetime):
                repo["created_at"] = repo["created_at"].strftime("%Y-%m-%d")
            if isinstance(repo.get("updated_at"), datetime.datetime):
                repo["updated_at"] = repo["updated_at"].strftime("%Y-%m-%d")
            repos.append(repo)

        print(f"REPO\n{repos},{len(repos)}")
        return render_template("public_repositories.html", user=user_doc, repos=repos)    

    except Exception as e:
        logger.error(f"Error fetching or saving user data: {e}")
        return redirect(url_for("main.login_page"))


@main_routes.route("/api/repo/<repo_id>/details")
def get_repo_details(repo_id):
    """Get detailed information about a repository"""
    if not github.authorized:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        repo = repositories_collection.find_one({"_id": ObjectId(repo_id)})
    
        if not repo:
            return jsonify({"error": "Repository not found"}), 404

        owner = user_collection.find_one({"_id": repo.get("user_id")})
        files_count = files_collection.count_documents({"repo_id": ObjectId(repo_id)})
        
        # Get members (if you have a members collection)
        # For now, just include the owner
        members = []
        if owner:
            members.append({
                "username": owner.get("username"),
                "avatar_url": owner.get("avatar_url"),
                "role": "Owner"
            })

        # Format response
        repo_details = {
            "_id": str(repo["_id"]),
            "name": repo.get("name"),
            "description": repo.get("description", "No description provided"),
            "private": repo.get("private", False),
            "owner": owner.get("username") if owner else "Unknown",
            "created_at": repo.get("created_at").strftime("%Y-%m-%d") if repo.get("created_at") else "Unknown",
            "members": members,
            "files_count": files_count
        }

        return jsonify(repo_details), 200

    except Exception as e:
        logger.error(f"Error fetching repository details: {e}")
        return jsonify({"error": "Internal server error"}), 500


# Join repository endpoint
@main_routes.route("/api/repo/<repo_id>/join", methods=["POST"])
def join_repository(repo_id):
    """Handle request to join a repository"""


    # Get the api so it can apply to the github when users 

    if not github.authorized:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Get current GitHub user
        resp = github.get("/user")
        if not resp.ok:
            return jsonify({"error": "Failed to fetch user data"}), 400
        
        user_data = resp.json()
        github_id = user_data['id']

        # Find user in DB
        user_doc = user_collection.find_one({"github_id": github_id})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404

        # Fetch repo
        repo = repositories_collection.find_one({"_id": ObjectId(repo_id)})
        if not repo:
            return jsonify({"error": "Repository not found"}), 404

        # Check if already a member
        existing = repositories_collection.find_one({
            "_id": ObjectId(repo_id),
            "members": github_id
        })

        if existing:
            return jsonify({"message": "User already in members"}), 409

        # Add member
        repositories_collection.update_one(
            {"_id": ObjectId(repo_id)},
            {"$push": {"members": github_id}}
        )

        # For now, just create a notification 
        # You can store join requests in a separate collection #
        # join_requests_collection.insert_one({ # "repo_id": ObjectId(repo_id), # 
        # "user_id": user_doc["_id"], # "status": "pending", 
        # "created_at": datetime.datetime.utcnow() # })

        print(
            f"User {user_doc['username']} joined repository {repo['name']}"
        )

        return jsonify({
            "message": "Joined repository successfully",
            "repo_name": repo["name"]
        }), 200

    except Exception as e:
        logger.error(f"Error joining repository: {e}")
        return jsonify({"error": "Internal server error"}), 500

    





@main_routes.route("/activity_feed")
def activity_feed():

    logger.info("Accessing activity feed page...")
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
            # Create new user if doesn't exist
            insert_result = user_collection.insert_one({
                "github_id": github_id,
                "username": github_username,
                "html_url": user_data['html_url'],
                "avatar_url": user_data['avatar_url'],
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow()
            })
            user_doc = user_collection.find_one({"_id": insert_result.inserted_id})

        return render_template("activity_feed.html", user=user_doc)    

    except Exception as e:
        logger.error(f"Error fetching or saving user data: {e}")
        return redirect(url_for("main.login_page"))
    
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
