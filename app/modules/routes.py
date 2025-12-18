from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from flask_dance.contrib.github import github
from .database import *
import logging
import datetime
import json
from bson import ObjectId
from .repository.routes import log_activity
from .repository.helper_functions import *


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

        # Check/create/update user in DB
        existing_user = user_collection.find_one({"github_id": github_id})
        if existing_user:
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
            insert_result = user_collection.insert_one({
                "github_id": github_id,
                "username": github_username,
                "html_url": user_data.get('html_url'),
                "avatar_url": user_data.get('avatar_url'),
                "created_at": datetime.datetime.utcnow(),
                "updated_at": datetime.datetime.utcnow()
            })
            user_doc = user_collection.find_one({"_id": insert_result.inserted_id})

        # 🔹 Redis caching for per-user repos
        redis_key = f"homepage:user:{github_id}:repos"
        cached_repos = redis_client.get(redis_key)
        if cached_repos:
            repos = json.loads(cached_repos)
            logger.info(f"Repos loaded from Redis cache for user {github_username}")

        else:
            repos_cursor = repositories_collection.find({
                "$or": [
                    {"owner_github_id": github_id},
                    {"members": github_id}
                ]
            }).sort("created_at", -1)

            repos = []
            for repo in repos_cursor:
                repo["is_owner"] = repo.get("owner_github_id") == github_id
                repo["members"] = repo.get("members", [])
                repo["_id"] = str(repo["_id"])  # convert repo _id

                # If there’s a parent_id or nested ObjectId
                if repo.get("parent_id"):
                    repo["parent_id"] = str(repo["parent_id"])

                if isinstance(repo.get("created_at"), datetime.datetime):
                    repo["created_at"] = repo["created_at"].strftime("%Y-%m-%d")
                if isinstance(repo.get("updated_at"), datetime.datetime):
                    repo["updated_at"] = repo["updated_at"].strftime("%Y-%m-%d")

                repos.append(repo)


            # Cache repos in Redis for 2 minutes
            repos_to_cache = convert_objectids(repos)
            redis_client.setex(redis_key, 120, json.dumps(repos_to_cache))

            logger.info(f"Repos cached in Redis for user {github_username}")

        # Debug logging
        logger.info(f"User {github_username} (ID: {github_id}) has access to {len(repos)} repos")

        return render_template(
            "home_page.html",
            user=user_doc,
            repos=repos,
            current_github_id=github_id
        )

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

        # Get owner information
        owner = user_collection.find_one({"_id": repo.get("user_id")})
        
        # Count files in repository
        files_count = files_collection.count_documents({
            "repo_id": ObjectId(repo_id),
            "type": "file"  # Only count files, not folders
        })
        
        # Get member GitHub IDs from repo
        member_github_ids = repo.get("members", [])
        
        # Fetch member details from user collection
        members = []
        
        # Add owner first
        if owner:
            members.append({
                "username": owner.get("username"),
                "avatar_url": owner.get("avatar_url"),
                "github_id": owner.get("github_id"),
                "role": "Owner"
            })
        
        # Add other members
        if member_github_ids:
            member_users = user_collection.find({
                "github_id": {"$in": member_github_ids}
            })
            
            for member_user in member_users:
                # Don't duplicate owner
                if member_user.get("github_id") != owner.get("github_id"):
                    members.append({
                        "username": member_user.get("username"),
                        "avatar_url": member_user.get("avatar_url"),
                        "github_id": member_user.get("github_id"),
                        "role": "Member"
                    })

        # Format response
        repo_details = {
            "_id": str(repo["_id"]),
            "name": repo.get("name"),
            "description": repo.get("description", "No description provided"),
            "private": repo.get("private", False),
            "owner": owner.get("username") if owner else "Unknown",
            "owner_avatar": owner.get("avatar_url") if owner else None,
            "created_at": repo.get("created_at").strftime("%Y-%m-%d") if repo.get("created_at") else "Unknown",
            "members": members,
            "members_count": len(members),  
            "files_count": files_count
        }

        return jsonify(repo_details), 200

    except Exception as e:
        logger.error(f"Error fetching repository details: {e}")
        import traceback
        traceback.print_exc()
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
        
        repo_owner_id = repo.get("user_id")  
        repo_name = repo.get("name")
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
        log_activity(
            user_doc["_id"],
            "join_repo",
            f"Joined repository '{repo['name']}'",
            f"{user_doc['username']} joined the repository {repo['name']}",
            repo_id=repo["_id"],
            repo_name=repo_name
        )

        notification_details = {
            "user_id": repo_owner_id,  # the owner of the repository
            "type": "member_joined",
            "message": f"{user_doc['username']} joined your repository {repo_name}.",
            "repo_id": repo_id,
            "created_at": datetime.datetime.utcnow(),
            "read": False
        }

        notifications_collection.insert_one(notification_details)

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




@main_routes.route("/api/notifications")
def get_notifications():
    """Fetch notifications for the authenticated user"""
    if not github.authorized:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Get current user
        resp = github.get("/user")
        if not resp.ok:
            return jsonify({"error": "Failed to fetch user data"}), 400
        
        user_data = resp.json()
        github_id = user_data['id']
        
        # Find user in DB
        user_doc = user_collection.find_one({"github_id": github_id})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Fetch notifications for this user (sorted by newest first)
        notifications_cursor = notifications_collection.find({
            "user_id": user_doc["_id"]
        }).sort("created_at", -1).limit(50)  # Limit to 50 most recent
        
        notifications = []
        for notification in notifications_cursor:
            notifications.append({
                "id": str(notification["_id"]),
                "type": notification.get("type"),
                "message": notification.get("message"),
                "repo_id": str(notification.get("repo_id")) if notification.get("repo_id") else None,
                "created_at": notification.get("created_at").isoformat() if notification.get("created_at") else None,
                "read": notification.get("read", False)
            })
        
        return jsonify({"notifications": notifications}), 200
        
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Internal server error"}), 500


@main_routes.route("/api/notifications/<notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    """Mark a specific notification as read"""
    if not github.authorized:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Get current user
        resp = github.get("/user")
        if not resp.ok:
            return jsonify({"error": "Failed to fetch user data"}), 400
        
        user_data = resp.json()
        github_id = user_data['id']
        
        user_doc = user_collection.find_one({"github_id": github_id})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Mark notification as read
        result = notifications_collection.update_one(
            {
                "_id": ObjectId(notification_id),
                "user_id": user_doc["_id"]
            },
            {"$set": {"read": True}}
        )
        
        if result.modified_count > 0:
            return jsonify({"message": "Notification marked as read"}), 200
        else:
            return jsonify({"error": "Notification not found or already read"}), 404
            
    except Exception as e:
        logger.error(f"Error marking notification as read: {e}")
        return jsonify({"error": "Internal server error"}), 500


@main_routes.route("/api/notifications/mark_all_read", methods=["POST"])
def mark_all_notifications_read():
    """Mark all notifications as read for the authenticated user"""
    if not github.authorized:
        return jsonify({"error": "Unauthorized"}), 401
    
    try:
        # Get current user
        resp = github.get("/user")
        if not resp.ok:
            return jsonify({"error": "Failed to fetch user data"}), 400
        
        user_data = resp.json()
        github_id = user_data['id']
        
        user_doc = user_collection.find_one({"github_id": github_id})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Mark all notifications as read
        result = notifications_collection.update_many(
            {"user_id": user_doc["_id"], "read": False},
            {"$set": {"read": True}}
        )
        
        return jsonify({
            "message": "All notifications marked as read",
            "count": result.modified_count
        }), 200
        
    except Exception as e:
        logger.error(f"Error marking all notifications as read: {e}")
        return jsonify({"error": "Internal server error"}), 500