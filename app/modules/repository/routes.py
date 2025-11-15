from flask import Blueprint, jsonify, request,render_template,redirect,url_for
from flask_dance.contrib.github import github
from ..database import *
import logging
import requests
import datetime
import json
from bson import ObjectId

repo_routes = Blueprint("repo", __name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PISTON_URL = os.getenv("PISTON_URL", "http://piston:2000")


# -----------------------------
# Helper to serialize Mongo documents with ObjectId
# -----------------------------
def serialize_doc(doc):
    """
    Convert ObjectId fields in a dict to strings so it can be JSONified.
    """
    doc_copy = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            doc_copy[k] = str(v)
        elif isinstance(v, datetime.datetime):
            doc_copy[k] = v.isoformat()
        else:
            doc_copy[k] = v
    return doc_copy


# -----------------------------
# Create a new repository
# -----------------------------
@repo_routes.route("/create_repo", methods=["POST"])
def create_repo():
    logger.info("Creating a new repository...")
    
    if not github.authorized:
        return jsonify({"message": "User not authenticated with GitHub"}), 401

    token = github.token.get("access_token") if github.token else None
    if not token:
        return jsonify({"message": "Invalid GitHub token"}), 401

    data = request.get_json()
    repo_name = data.get("name")
    description = data.get("description", "")
    private = data.get("private", False)

    if not repo_name:
        return jsonify({"message": "Repository name is required"}), 400

    try:
        # Get GitHub user info
        user_resp = github.get("/user")
        if not user_resp.ok:
            raise Exception("Failed to fetch GitHub user details")
        user_data = user_resp.json()
        github_username = user_data["login"]

        # Find user in DB
        user_doc = user_collection.find_one({"username": github_username})
        if not user_doc:
            return jsonify({"message": "User not found in database"}), 404

        # Check if repo already exists for this user
        existing_repo = repositories_collection.find_one({
            "user_id": user_doc["_id"],
            "name": {"$regex": f"^{repo_name}$", "$options": "i"}
        })
        if existing_repo:
            return jsonify({"message": f"Repository '{repo_name}' already exists"}), 409

        # Create repository on GitHub
        headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}
        payload = {"name": repo_name, "description": description, "private": private}
        response = requests.post("https://api.github.com/user/repos", headers=headers, json=payload)

        if response.status_code != 201:
            return jsonify({"message": "Failed to create repository on GitHub", "details": response.json()}), response.status_code

        # Save repo in DB
        repo_data = response.json()
        repo_doc = {
            "user_id": user_doc["_id"],
            "github_id": repo_data["id"],
            "name": repo_data["name"],
            "full_name": repo_data["full_name"],
            "html_url": repo_data["html_url"],
            "description": repo_data.get("description"),
            "private": repo_data["private"],
            "created_at": datetime.datetime.strptime(repo_data["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": datetime.datetime.utcnow()
        }
        insert_result = repositories_collection.insert_one(repo_doc)

        # Fetch the saved document and serialize ObjectIds
        saved_repo = repositories_collection.find_one({"_id": insert_result.inserted_id})
        saved_repo_serialized = serialize_doc(saved_repo)

        logger.info(f"Repository '{repo_name}' added to DB for user '{github_username}'")

        return jsonify({
            "message": f"Repository '{repo_name}' created successfully",
            "repo": saved_repo_serialized
        }), 201

    except Exception as e:
        logger.error(f"Error creating repository: {e}")
        return jsonify({"message": "Error creating repository", "error": str(e)}), 500


# -----------------------------
# Access a repository page
# -----------------------------

@repo_routes.route("/repo/<repo_id>")
def repo_page(repo_id):
    logger.info(f"Accessing repository page: {repo_id}")

    if not github.authorized:
        return redirect(url_for("main.login_page"))

    try:
        # Get GitHub user info
        user_resp = github.get("/user")
        if not user_resp.ok:
            raise Exception("Failed to fetch GitHub user data")
        github_username = user_resp.json()["login"]

        # Find user in DB
        user_doc = user_collection.find_one({"username": github_username})
        if not user_doc:
            return redirect(url_for("main.home"))

        # Convert repo_id to ObjectId
        repo_obj_id = ObjectId(repo_id)

        # Find repository owned by this user
        repo_doc = repositories_collection.find_one({
            "_id": repo_obj_id,
            "user_id": user_doc["_id"]
        })
        if not repo_doc:
            return redirect(url_for("main.home"))

        # Fetch all files in this repo
        files = list(files_collection.find({"repo_id": repo_doc["_id"]}))

        # Prepare file data for frontend
        files_data = [{
            "id": str(f["_id"]),
            "path": f["path"],
            "language": f["language"],
            "content": f["content"]
        } for f in files]

        return render_template(
            "code_editor.html",
            repo=repo_doc,
            user=user_doc,
            files=files_data
        )

    except Exception as e:
        logger.error(f"Error accessing repository page: {e}")
        return redirect(url_for("main.home"))



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