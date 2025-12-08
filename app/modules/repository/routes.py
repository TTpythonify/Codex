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

# ---------------------------
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

@repo_routes.route("/create_repo", methods=["POST"])
def create_repo():

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
        github_user_id = user_data["id"]

        print(f"\n\n{user_data}\n")

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
        print(f"\n\n{github_user_id}\n")
        repo_doc = {
            "user_id": user_doc["_id"],           # MongoDB _id of owner
            "owner_github_id": github_user_id,    # GitHub ID of the user (owner)
            "repo_github_id": repo_data["id"],    # GitHub ID of the repo
            "name": repo_data["name"],
            "full_name": repo_data["full_name"],
            "html_url": repo_data["html_url"],
            "description": repo_data.get("description"),
            "private": repo_data["private"],
            "created_at": datetime.datetime.strptime(repo_data["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
            "updated_at": datetime.datetime.utcnow(),
            "members": []
        }

        insert_result = repositories_collection.insert_one(repo_doc)

        # Fetch the saved document and serialize ObjectIds
        saved_repo = repositories_collection.find_one({"_id": insert_result.inserted_id})
        saved_repo_serialized = serialize_doc(saved_repo)

        log_activity(
            user_doc["_id"],
            "create_repo",
            f"Created repository '{repo_name}'",
            f"New repository created with {'private' if private else 'public'} visibility",
            repo_id=insert_result.inserted_id,
            repo_name=repo_name,
            metadata={"private": private, "description": description}
        )

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
            logger.error(f"User {github_username} not found in database")
            return redirect(url_for("main.home"))

        # Convert repo_id to ObjectId - ADD VALIDATION HERE
        try:
            repo_obj_id = ObjectId(repo_id)
        except Exception as e:
            logger.error(f"Invalid repo_id format: {repo_id}, error: {e}")
            return redirect(url_for("main.home"))

        # Find repository owned by this user
        repo_doc = repositories_collection.find_one({
            "_id": repo_obj_id,
            "user_id": user_doc["_id"]
        })
        
        if not repo_doc:
            logger.error(f"Repository {repo_id} not found or not owned by user {github_username}")
            return redirect(url_for("main.home"))

        return render_template(
            "code_editor.html",
            repo=repo_doc,
            user=user_doc
        )

    except Exception as e:
        logger.error(f"Error accessing repository page: {e}")
        import traceback
        traceback.print_exc()
        return redirect(url_for("main.home"))


@repo_routes.route("/run_code", methods=["POST"])
def run_code():
    data = request.get_json()
    code = data.get("code", "")
    language = data.get("language", "text")
    file_id = data.get("file_id")

    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    if len(code) > 50000:
        return jsonify({"error": "Code too long (max 50KB)"}), 400

    if language == "text":
        return

    # Map frontend language to Piston language identifiers
    language_map = {
        'python': 'python',
        'javascript': 'javascript',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c'
    }
    piston_language = language_map.get(language, 'python')

    # Determine filename for Java or default
    if language == 'java':
        import re
        class_match = re.search(r'public\s+class\s+(\w+)', code)
        filename = f"{class_match.group(1)}.java" if class_match else "Main.java"
    else:
        file_extension_map = {
            'python': 'py',
            'javascript': 'js',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c'
        }
        filename = f"main.{file_extension_map.get(language, 'txt')}"

    execution_data = {
        "language": piston_language,
        "code": code
    }

    try:
        # Use your Render Piston endpoint
        response = requests.post(PISTON_URL, json=execution_data, timeout=15)
        response.raise_for_status()
        result = response.json()

        # Extract stdout and stderr
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = 0 if not stderr else 1

        # Determine output and success
        if exit_code != 0:
            output = f"Error:\n{stderr}"
            success = False
        else:
            output = stdout if stdout else "No output"
            success = True

        # ✅ Update file in DB and log activity
        if success and file_id:
            try:
                if github.authorized:
                    user_resp = github.get("/user")
                    if user_resp.ok:
                        github_username = user_resp.json()["login"]
                        user_doc = user_collection.find_one({"username": github_username})

                        if user_doc:
                            file_obj_id = ObjectId(file_id)
                            file_doc = files_collection.find_one({"_id": file_obj_id})
                            repo_doc = repositories_collection.find_one(
                                {"_id": file_doc["repo_id"]}) if file_doc else None

                            update_result = files_collection.update_one(
                                {"_id": file_obj_id, "user_id": user_doc["_id"], "type": "file"},
                                {"$set": {
                                    "content": code,
                                    "last_success_at": datetime.datetime.utcnow(),
                                    "updated_at": datetime.datetime.utcnow()
                                }}
                            )

                            if update_result.modified_count > 0:
                                logger.info(f"✅ File {file_id} saved after successful execution")
                                if file_doc and repo_doc:
                                    log_activity(
                                        user_doc["_id"],
                                        "run_code",
                                        f"Executed {file_doc.get('name', 'file')}",
                                        f"Successfully ran {language} code in {repo_doc['name']}",
                                        repo_id=repo_doc["_id"],
                                        repo_name=repo_doc["name"],
                                        file_name=file_doc.get("name"),
                                        language=language,
                                        metadata={"lines": len(code.split('\n'))}
                                    )
                            else:
                                logger.warning(f"⚠️ File {file_id} not found or not updated")
            except Exception as e:
                logger.error(f"❌ Error saving file after execution: {e}")

        return jsonify({
            "output": output,
            "success": success,
            "compile_stdout": "",  # not used in Render Piston
            "compile_stderr": ""   # not used in Render Piston
        })

    except requests.exceptions.Timeout:
        logger.error("Piston execution timeout")
        return jsonify({"error": "Execution timeout (max 15 seconds)"}), 408

    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with Piston: {e}")
        return jsonify({"error": f"Could not execute code: {str(e)}"}), 500

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500





@repo_routes.route("/create_folder", methods=["POST"])
def create_folder():
    try:
        if not github.authorized:
            return jsonify({"error": "Not authenticated with GitHub"}), 401
        
        data = request.get_json()
        repo_id = data.get("repo_id")
        folder_name = data.get("folder_name")
        parent_id = data.get("parent_id")  # None for root
        
        if not repo_id or not folder_name or not folder_name.strip():
            return jsonify({"error": "Repository ID and folder name are required"}), 400
        
        folder_name = folder_name.strip()
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in folder_name for char in invalid_chars):
            return jsonify({"error": f"Folder name cannot contain: {', '.join(invalid_chars)}"}), 400
        
        # Get authenticated user
        user_resp = github.get("/user")
        if not user_resp.ok:
            return jsonify({"error": "Failed to fetch GitHub user details"}), 401
        github_username = user_resp.json()["login"]
        user_doc = user_collection.find_one({"username": github_username})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404

        # Verify repository
        try:
            repo_obj_id = ObjectId(repo_id)
        except Exception:
            return jsonify({"error": "Invalid repository ID"}), 400

        repo_doc = repositories_collection.find_one({"_id": repo_obj_id, "user_id": user_doc["_id"]})
        if not repo_doc:
            return jsonify({"error": "Repository not found or access denied"}), 404

        # Handle parent folder
        parent_obj_id = None
        parent_path = ""
        if parent_id:
            try:
                parent_obj_id = ObjectId(parent_id)
            except Exception:
                return jsonify({"error": "Invalid parent ID"}), 400
            parent_doc = files_collection.find_one({
                "_id": parent_obj_id,
                "repo_id": repo_doc["_id"],
                "user_id": user_doc["_id"]
            })
            if not parent_doc or parent_doc.get("type") != "folder":
                return jsonify({"error": "Parent must be a valid folder"}), 400
            parent_path = parent_doc.get("path", "")

        # Build full path
        full_path = f"{parent_path}/{folder_name}" if parent_path else folder_name

        # Duplicate check for folder
        existing_folder = files_collection.find_one({
            "repo_id": repo_doc["_id"],
            "parent_id": parent_obj_id,
            "name": folder_name,
            "type": "folder"
        })
        if existing_folder:
            return jsonify({"error": f"A folder named '{folder_name}' already exists in this location"}), 409

        # Create folder document
        folder_doc = {
            "repo_id": repo_doc["_id"],
            "user_id": user_doc["_id"],
            "type": "folder",
            "name": folder_name,
            "parent_id": parent_obj_id,
            "path": full_path,
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow()
        }

        insert_result = files_collection.insert_one(folder_doc)
        saved_folder = files_collection.find_one({"_id": insert_result.inserted_id})
        saved_folder_serialized = serialize_doc(saved_folder)

        log_activity(
            user_doc["_id"],
            "create_folder",
            f"Created folder '{folder_name}'",
            f"New folder created in {repo_doc['name']}",
            repo_id=repo_doc["_id"],
            repo_name=repo_doc["name"],
            file_name=folder_name
        )

        return jsonify({
            "message": f"Folder '{folder_name}' created successfully",
            "folder": saved_folder_serialized
        }), 201

    except Exception as e:
        logger.error(f"Error creating folder: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to create folder: {str(e)}"}), 500

    
    
@repo_routes.route("/create_file", methods=["POST"])
def create_file():
    try:
        # 1. Authentication
        if not github.authorized:
            return jsonify({"error": "Not authenticated with GitHub"}), 401

        data = request.get_json()
        repo_id = data.get("repo_id")
        file_name = data.get("file_name")
        language = data.get("language", "text")
        content = data.get("content", "")
        parent_id = data.get("parent_id")
        warning_msg = None

        # 2. Validate fields
        if not repo_id or not file_name or not file_name.strip():
            return jsonify({"error": "Repository ID and file name are required"}), 400
        file_name = file_name.strip()

        allowed_languages = ['python', 'javascript', 'java', 'cpp', 'c','text']
        if language not in allowed_languages:
            return jsonify({"error": f"Language must be one of: {', '.join(allowed_languages)}"}), 400

        # 3. Invalid characters check
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in file_name for char in invalid_chars):
            return jsonify({"error": f"File name cannot contain: {', '.join(invalid_chars)}"}), 400

        # 4. Get user
        user_resp = github.get("/user")
        if not user_resp.ok:
            return jsonify({"error": "Failed to fetch GitHub user details"}), 401
        github_username = user_resp.json()["login"]
        user_doc = user_collection.find_one({"username": github_username})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404

        # 5. Verify repository
        try:
            repo_obj_id = ObjectId(repo_id)
        except Exception:
            return jsonify({"error": "Invalid repository ID"}), 400

        repo_doc = repositories_collection.find_one({"_id": repo_obj_id, "user_id": user_doc["_id"]})
        if not repo_doc:
            return jsonify({"error": "Repository not found or access denied"}), 404

        # 6. Handle parent folder
        parent_obj_id = None
        parent_path = ""
        if parent_id:
            try:
                parent_obj_id = ObjectId(parent_id)
            except Exception:
                return jsonify({"error": "Invalid parent ID"}), 400
            parent_doc = files_collection.find_one({
                "_id": parent_obj_id,
                "repo_id": repo_doc["_id"],
                "user_id": user_doc["_id"]
            })
            if not parent_doc or parent_doc.get("type") != "folder":
                return jsonify({"error": "Parent must be a valid folder"}), 400
            parent_path = parent_doc.get("path", "")

        # 7. Adjust filename for Java
        if language == "java":
            from .helper_functions import to_java_class_name
            class_name = to_java_class_name(file_name)
            file_name = f"{class_name}.java"

        # 8. Build full path
        full_path = f"{parent_path}/{file_name}" if parent_path else file_name

        # 9. Duplicate check (works for all languages)
        existing_file = files_collection.find_one({
            "repo_id": repo_doc["_id"],
            "parent_id": parent_obj_id,
            "name": file_name,
            "type": "file"
        })
        if existing_file:
            return jsonify({"error": f"A file named '{file_name}' already exists in this folder"}), 409

        # 10. Prepare file content templates
        if language == "java":
            content = f"""public class {class_name} {{
    public static void main(String[] args) {{
        // NOTE: Java programs typically take 10–15 seconds to run due to setup complexity
    }}
}}"""
        elif language == "c":
            content = """#include <stdio.h>

int main() {
    // Code goes here
    return 0;
}"""

        elif language == "cpp":
            content = """#include <iostream>

int main() {
    // code goes here
    return 0;
}"""




#include <stdio.h>

        # 11. Insert into DB
        file_doc = {
            "repo_id": repo_doc["_id"],
            "user_id": user_doc["_id"],
            "type": "file",
            "name": file_name,
            "parent_id": parent_obj_id,
            "path": full_path,
            "language": language,
            "content": content,
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow()
        }

        insert_result = files_collection.insert_one(file_doc)
        saved_file = files_collection.find_one({"_id": insert_result.inserted_id})
        saved_file_serialized = serialize_doc(saved_file)
        log_activity(
            user_doc["_id"],
            "create_file",
            f"Created file '{file_name}'",
            f"New {language} file created in {repo_doc['name']}",
            repo_id=repo_doc["_id"],
            repo_name=repo_doc["name"],
            file_name=file_name,
            language=language
        )

        return jsonify({
            "message": f"File '{file_name}' created successfully",
            "file": saved_file_serialized
        }), 201

    except Exception as e:
        logger.error(f"Error creating file: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Failed to create file: {str(e)}"}), 500


    


@repo_routes.route("/get_files/<repo_id>", methods=["GET"])
def get_files(repo_id):
    """
    Retrieves all files AND folders for a given repository
    """
    logger.info(f"Fetching files for repository: {repo_id}")
    
    try:
        # Step 1: Check if user is authenticated
        if not github.authorized:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Step 2: Convert repo_id to ObjectId
        try:
            repo_obj_id = ObjectId(repo_id)
        except Exception as e:
            logger.error(f"Invalid repo_id format: {e}")
            return jsonify({"error": "Invalid repository ID"}), 400
        
        # Step 3: Get authenticated user information
        user_resp = github.get("/user")
        if not user_resp.ok:
            return jsonify({"error": "Failed to fetch user details"}), 401
        github_username = user_resp.json()["login"]
        
        # Step 4: Find user in database
        user_doc = user_collection.find_one({"username": github_username})
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Step 5: Verify repository exists and belongs to user
        repo_doc = repositories_collection.find_one({
            "_id": repo_obj_id,
            "user_id": user_doc["_id"]
        })
        
        if not repo_doc:
            return jsonify({"error": "Repository not found"}), 404
        
        # Step 6: Fetch ALL items (files AND folders) for this repository
        items_cursor = files_collection.find({"repo_id": repo_doc["_id"]})
        items = list(items_cursor)
        
        # Step 7: Serialize all items
        serialized_items = []
        for item in items:
            serialized_item = {
                "id": str(item["_id"]),
                "type": item.get("type", "file"),  # "file" or "folder"
                "name": item.get("name", ""),
                "path": item.get("path", ""),
                "parent_id": str(item["parent_id"]) if item.get("parent_id") else None,
                "created_at": item.get("created_at").isoformat() if item.get("created_at") else None,
                "updated_at": item.get("updated_at").isoformat() if item.get("updated_at") else None
            }
            
            # Add file-specific fields only for files
            if item.get("type") == "file":
                serialized_item["language"] = item.get("language", "")
                serialized_item["content"] = item.get("content", "")
            
            serialized_items.append(serialized_item)

        return jsonify({"files": serialized_items}), 200
    
    except Exception as e:
        logger.error(f"Error fetching files: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
    






@repo_routes.route("/get_activities", methods=["GET"])
def get_activities():
    """
    Fetch recent activities for the authenticated user
    """
    try:
        if not github.authorized:
            return jsonify({"error": "Not authenticated"}), 401
        
        # Get user
        user_resp = github.get("/user")
        if not user_resp.ok:
            return jsonify({"error": "Failed to fetch user details"}), 401
        github_username = user_resp.json()["login"]
        user_doc = user_collection.find_one({"username": github_username})
        
        if not user_doc:
            return jsonify({"error": "User not found"}), 404
        
        # Get limit from query params (default 20)
        limit = int(request.args.get('limit', 20))
        
        # Fetch activities from database, sorted by timestamp descending
        activities_cursor = db["codex_activities"].find(
            {"user_id": user_doc["_id"]}
        ).sort("timestamp", -1).limit(limit)
        
        activities = []
        for activity in activities_cursor:
            activities.append({
                "id": str(activity["_id"]),
                "type": activity.get("type"),
                "title": activity.get("title"),
                "description": activity.get("description"),
                "repo_name": activity.get("repo_name"),
                "repo_id": str(activity.get("repo_id")) if activity.get("repo_id") else None,
                "file_name": activity.get("file_name"),
                "language": activity.get("language"),
                "timestamp": activity.get("timestamp").isoformat() if activity.get("timestamp") else None,
                "metadata": activity.get("metadata", {})
            })
        
        return jsonify({"activities": activities}), 200
        
    except Exception as e:
        logger.error(f"Error fetching activities: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500



def log_activity(user_id, activity_type, title, description, **kwargs):
    """
    Log a user activity to the database
    
    Args:
        user_id: ObjectId of the user
        activity_type: Type of activity (create_repo, create_file, run_code, etc.)
        title: Short title for the activity
        description: Detailed description
        **kwargs: Additional metadata (repo_id, repo_name, file_name, language, etc.)
    """
    try:
        activity_doc = {
            "user_id": user_id,
            "type": activity_type,
            "title": title,
            "description": description,
            "timestamp": datetime.datetime.utcnow(),
            "metadata": {}
        }
        
        # Add optional fields
        if 'repo_id' in kwargs:
            activity_doc['repo_id'] = kwargs['repo_id']
        if 'repo_name' in kwargs:
            activity_doc['repo_name'] = kwargs['repo_name']
        if 'file_name' in kwargs:
            activity_doc['file_name'] = kwargs['file_name']
        if 'language' in kwargs:
            activity_doc['language'] = kwargs['language']
        if 'metadata' in kwargs:
            activity_doc['metadata'] = kwargs['metadata']
        
        db["codex_activities"].insert_one(activity_doc)
        logger.info(f"✅ Activity logged: {activity_type} for user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Failed to log activity: {e}")


