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

        # Fetch all files in this repo - NO NEED TO PASS TO TEMPLATE
        # Files will be loaded via AJAX call from frontend
        logger.info(f"Successfully loaded repository page for {repo_doc['name']}")

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
    logger.info("Code execution requested")

    # Get code and language from frontend
    data = request.get_json()
    code = data.get("code", "")
    language = data.get("language", "python")  # Get language from request
    
    if not code.strip():
        return jsonify({"error": "No code provided"}), 400

    # Basic validation
    if len(code) > 50000:  
        return jsonify({"error": "Code too long (max 50KB)"}), 400

    # Map frontend language to Piston language identifiers
    language_map = {
        'python': 'python',
        'javascript': 'javascript',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c'
    }
    
    # Map languages to their file extensions
    file_extension_map = {
        'python': 'py',
        'javascript': 'js',
        'java': 'java',
        'cpp': 'cpp',
        'c': 'c'
    }
    
    piston_language = language_map.get(language, 'python')
    file_extension = file_extension_map.get(language, 'py')
    
    # Determine the filename based on language
    if language == 'java':
        # For Java, we need to extract the class name
        import re
        class_match = re.search(r'public\s+class\s+(\w+)', code)
        filename = f"{class_match.group(1)}.java" if class_match else "Main.java"
    else:
        filename = f"main.{file_extension}"

    # Piston API format
    execution_data = {
        "language": piston_language,
        "version": "*",
        "files": [
            {
                "name": filename,
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

    try:
        # Send code to Piston service
        response = requests.post(
            f"{PISTON_URL}/api/v2/execute",
            json=execution_data,
            timeout=15
        )
        response.raise_for_status()
        result = response.json()


        # Get output from compile (for compiled languages) and run
        compile_result = result.get("compile", {})
        run_result = result.get("run", {})
        
        compile_stdout = compile_result.get("stdout", "")
        compile_stderr = compile_result.get("stderr", "")
        compile_code = compile_result.get("code", 0)
        
        stdout = run_result.get("stdout", "")
        stderr = run_result.get("stderr", "")
        exit_code = run_result.get("code", 0)


        # Check for compilation errors first (for compiled languages)
        if compile_code != 0 and compile_stderr:
            output = f"Compilation Error:\n{compile_stderr}"
            success = False
        else:
            # Combine outputs
            output = stdout if stdout else (stderr if stderr else "No output")
            
            # Check for runtime errors
            if exit_code != 0:
                output = f"Runtime Error (exit code {exit_code}):\n{output}"
                success = False
            else:
                success = True

        logger.info(f"Code executed with exit code: {exit_code}\n\n\nOUTPUT : {output}\n\n")

        # THe output i will store in thhe database now
        
        response_data = {
            "output": output,
            "success": success
        }
        
        return jsonify(response_data)

    except requests.exceptions.Timeout:
        logger.error("Piston execution timeout")
        logger.info("❌ ERROR: Piston execution timeout")
        return jsonify({"error": "Execution timeout (max 15 seconds)"}), 408
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error communicating with Piston: {e}")
        logger.info(f"❌ ERROR: Could not communicate with Piston: {e}")
        return jsonify({"error": f"Could not execute code: {str(e)}"}), 500
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.info(f"❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@repo_routes.route("/create_folder", methods=["POST"])
def create_folder():
    """
    Creates a new folder in the repository
    
    Expected JSON body:
    {
        "repo_id": "507f1f77bcf86cd799439011",
        "folder_name": "src",
        "parent_id": null  // or another folder's ID for nested folders
    }
    """
    logger.info("Folder creation requested")
    
    try:
        # Step 1: Check if user is authenticated with GitHub
        if not github.authorized:
            return jsonify({"error": "Not authenticated with GitHub"}), 401
        
        # Step 2: Get the request JSON data
        data = request.get_json()
        repo_id = data.get("repo_id")
        folder_name = data.get("folder_name")
        parent_id = data.get("parent_id")  # This can be None/null
        
        # Step 3: Validate required fields
        if not repo_id:
            return jsonify({"error": "Repository ID is required"}), 400
        
        if not folder_name or not folder_name.strip():
            return jsonify({"error": "Folder name is required"}), 400
        
        # Sanitize folder name (remove leading/trailing spaces, check for invalid characters)
        folder_name = folder_name.strip()
        
        # Check for invalid characters in folder name
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in folder_name for char in invalid_chars):
            return jsonify({"error": f"Folder name cannot contain: {', '.join(invalid_chars)}"}), 400
        
        # Step 4: Get the authenticated GitHub user information
        try:
            user_resp = github.get("/user")
            if not user_resp.ok:
                return jsonify({"error": "Failed to fetch GitHub user details"}), 401
            github_username = user_resp.json()["login"]
        except Exception as e:
            logger.error(f"Error fetching GitHub user: {e}")
            return jsonify({"error": "Failed to authenticate with GitHub"}), 401
        
        # Step 5: Find the user in the database
        user_doc = user_collection.find_one({"username": github_username})
        if not user_doc:
            return jsonify({"error": "User not found in database"}), 404
        
        # Step 6: Convert repo_id string to ObjectId
        try:
            repo_obj_id = ObjectId(repo_id)
        except Exception as e:
            logger.error(f"Invalid repo_id format: {e}")
            return jsonify({"error": "Invalid repository ID format"}), 400
        
        # Step 7: Find the repository in database and verify ownership
        repo_doc = repositories_collection.find_one({
            "_id": repo_obj_id,
            "user_id": user_doc["_id"]
        })
        
        if not repo_doc:
            return jsonify({"error": "Repository not found or access denied"}), 404
        
        # Step 8: Handle parent_id logic
        parent_obj_id = None
        parent_path = ""
        
        if parent_id:  # If parent_id is provided (not None, not empty string)
            try:
                parent_obj_id = ObjectId(parent_id)
            except Exception as e:
                logger.error(f"Invalid parent_id format: {e}")
                return jsonify({"error": "Invalid parent ID format"}), 400
            
            # Find the parent folder
            parent_doc = files_collection.find_one({
                "_id": parent_obj_id,
                "repo_id": repo_doc["_id"],
                "user_id": user_doc["_id"]
            })
            
            if not parent_doc:
                return jsonify({"error": "Parent folder not found"}), 404
            
            # Verify parent is a folder, not a file
            if parent_doc.get("type") != "folder":
                return jsonify({"error": "Parent must be a folder, not a file"}), 400
            
            # Get parent's path for building full path
            parent_path = parent_doc.get("path", "")
        
        # Step 9: Build the full path
        if parent_path:
            full_path = f"{parent_path}/{folder_name}"
        else:
            full_path = folder_name
        
        logger.info(f"Creating folder at path: {full_path}")
        
        # Step 10: Check if folder already exists at this location
        existing_folder = files_collection.find_one({
            "repo_id": repo_doc["_id"],
            "parent_id": parent_obj_id,
            "name": folder_name,
            "type": "folder"
        })
        
        if existing_folder:
            return jsonify({"error": f"A folder named '{folder_name}' already exists at this location"}), 409
        
        # Step 11: Create the folder document
        folder_doc = {
            "repo_id": repo_doc["_id"],
            "user_id": user_doc["_id"],
            "type": "folder",
            "name": folder_name,
            "parent_id": parent_obj_id,  # None for root-level, ObjectId for nested
            "path": full_path,
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow()
        }
        
        # Step 12: Insert the folder into the database
        insert_result = files_collection.insert_one(folder_doc)
        logger.info(f"Folder created with ID: {insert_result.inserted_id}")
        
        # Step 13: Fetch the newly created folder
        saved_folder = files_collection.find_one({"_id": insert_result.inserted_id})
        
        # Step 14: Serialize and return
        saved_folder_serialized = serialize_doc(saved_folder)
        
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
    logger.info("File creation requested")
    
    try:
        # Step 1: Check authentication
        if not github.authorized:
            return jsonify({"error": "Not authenticated with GitHub"}), 401
        
        # Step 2: Get request data
        data = request.get_json()
        repo_id = data.get("repo_id")
        file_name = data.get("file_name")
        language = data.get("language", "python")
        content = data.get("content", "")
        parent_id = data.get("parent_id")
        
        # Step 3: Validate required fields
        if not repo_id:
            return jsonify({"error": "Repository ID is required"}), 400
        
        if not file_name or not file_name.strip():
            return jsonify({"error": "File name is required"}), 400
        
        file_name = file_name.strip()
        
        # Validate language is one of the allowed ones
        allowed_languages = ['python', 'javascript', 'java', 'cpp', 'c']
        if language not in allowed_languages:
            return jsonify({"error": f"Language must be one of: {', '.join(allowed_languages)}"}), 400
        
        # Check for invalid characters in file name
        invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        if any(char in file_name for char in invalid_chars):
            return jsonify({"error": f"File name cannot contain: {', '.join(invalid_chars)}"}), 400
        
        # Step 4: Get authenticated user
        try:
            user_resp = github.get("/user")
            if not user_resp.ok:
                return jsonify({"error": "Failed to fetch GitHub user details"}), 401
            github_username = user_resp.json()["login"]
        except Exception as e:
            logger.error(f"Error fetching GitHub user: {e}")
            return jsonify({"error": "Failed to authenticate with GitHub"}), 401
        
        # Step 5: Find user in database
        user_doc = user_collection.find_one({"username": github_username})
        if not user_doc:
            return jsonify({"error": "User not found in database"}), 404
        
        # Step 6: Convert repo_id to ObjectId
        try:
            repo_obj_id = ObjectId(repo_id)
        except Exception as e:
            logger.error(f"Invalid repo_id format: {e}")
            return jsonify({"error": "Invalid repository ID format"}), 400
        
        # Step 7: Find repository and verify ownership
        repo_doc = repositories_collection.find_one({
            "_id": repo_obj_id,
            "user_id": user_doc["_id"]
        })
        
        if not repo_doc:
            return jsonify({"error": "Repository not found or access denied"}), 404
        
        # Step 8: Handle parent_id logic
        parent_obj_id = None
        parent_path = ""
        
        if parent_id:
            try:
                parent_obj_id = ObjectId(parent_id)
            except Exception as e:
                logger.error(f"Invalid parent_id format: {e}")
                return jsonify({"error": "Invalid parent ID format"}), 400
            
            # Find parent folder
            parent_doc = files_collection.find_one({
                "_id": parent_obj_id,
                "repo_id": repo_doc["_id"],
                "user_id": user_doc["_id"]
            })
            
            if not parent_doc:
                return jsonify({"error": "Parent folder not found"}), 404
            
            # Verify parent is a folder, not a file
            if parent_doc.get("type") != "folder":
                return jsonify({"error": "Cannot create file inside another file. Parent must be a folder"}), 400
            
            parent_path = parent_doc.get("path", "")
        
        # Step 9: Build full path
        if parent_path:
            full_path = f"{parent_path}/{file_name}"
        else:
            full_path = file_name
        
        logger.info(f"Creating file at path: {full_path}")
        
        # Step 10: Check if file already exists at this location
        existing_file = files_collection.find_one({
            "repo_id": repo_doc["_id"],
            "parent_id": parent_obj_id,
            "name": file_name,
            "type": "file"
        })
        
        if existing_file:
            return jsonify({"error": f"A file named '{file_name}' already exists at this location"}), 409
        
        # Step 11: Create file document
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
        
        # Step 12: Insert into database
        insert_result = files_collection.insert_one(file_doc)
        logger.info(f"File created with ID: {insert_result.inserted_id}")
        
        # Step 13: Fetch newly created file
        saved_file = files_collection.find_one({"_id": insert_result.inserted_id})
        
        # Step 14: Serialize and return
        saved_file_serialized = serialize_doc(saved_file)
        
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
        
        # Step 8: Return the items list
        logger.info(f"Found {len(serialized_items)} items in repository")
        return jsonify({"files": serialized_items}), 200
    
    except Exception as e:
        logger.error(f"Error fetching files: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500