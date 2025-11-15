from flask import Blueprint, render_template, redirect, url_for, session, jsonify, request
from flask_dance.contrib.github import github
from ..database import *
import logging
import requests
import json

repo_routes = Blueprint("repo", __name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)





@repo_routes.route("/create_repo", methods=["POST"])
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
@repo_routes.route("/repo/<int:repo_id>")
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




PISTON_URL = os.getenv("PISTON_URL", "http://piston:2000")




@repo_routes.route("/run_code", methods=["POST"])
def run_code():
    logger.info("Code execution requested")

    # Get code from frontend
    data = request.get_json()
    code = data.get("code", "")
    
    print("\n" + "="*60)
    print("📝 CODE RECEIVED:")
    print("="*60)
    print(code)
    print("="*60 + "\n")
    
    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    # Basic validation
    if len(code) > 50000:  # 50KB limit
        return jsonify({"error": "Code too long (max 50KB)"}), 400

    # Piston API format
    execution_data = {
        "language": "python",
        "version": "*",
        "files": [
            {
                "name": "main.py",
                "content": code
            }
        ],
        "stdin": "",
        "args": [],
        "compile_timeout": 10000,  # 10 seconds
        "run_timeout": 3000,       # 3 seconds
        "compile_memory_limit": -1,
        "run_memory_limit": -1
    }

    print("🚀 Sending request to Piston API...")
    print(f"   URL: {PISTON_URL}/api/v2/execute")
    
    try:
        # Send code to Piston service
        response = requests.post(
            f"{PISTON_URL}/api/v2/execute",
            json=execution_data,
            timeout=15
        )
        response.raise_for_status()
        result = response.json()

        print("\n" + "="*60)
        print("📦 PISTON RAW RESPONSE:")
        print("="*60)
        print(json.dumps(result, indent=2))
        print("="*60 + "\n")

        # Get output
        run_result = result.get("run", {})
        stdout = run_result.get("stdout", "")
        stderr = run_result.get("stderr", "")
        exit_code = run_result.get("code", 0)

        print("="*60)
        print("📊 PARSED RESULTS:")
        print("="*60)
        print(f"Exit Code: {exit_code}")
        print(f"STDOUT:\n{stdout if stdout else '(empty)'}")
        print(f"STDERR:\n{stderr if stderr else '(empty)'}")
        print("="*60 + "\n")

        # Combine outputs
        output = stdout if stdout else (stderr if stderr else "No output")

        # Check for errors
        if exit_code != 0:
            output = f"Error (exit code {exit_code}):\n{output}"

        logger.info(f"Code executed with exit code: {exit_code}")
        
        response_data = {
            "output": output,
            "success": exit_code == 0
        }
        
        print("="*60)
        print("✉️ RESPONSE TO FRONTEND:")
        print("="*60)
        print(json.dumps(response_data, indent=2))
        print("="*60 + "\n")
        
        return jsonify(response_data)

    except requests.exceptions.Timeout:
        logger.error("Piston execution timeout")
        print("❌ ERROR: Piston execution timeout")
        return jsonify({"error": "Execution timeout (max 15 seconds)"}), 408
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with Piston: {e}")
        print(f"❌ ERROR: Could not communicate with Piston: {e}")
        return jsonify({"error": f"Could not execute code: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500