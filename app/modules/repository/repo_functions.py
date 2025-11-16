# ============================================================================
# FILE CREATION BACKEND ROUTES - IMPLEMENTATION GUIDE
# ============================================================================
# Add these routes to your repo_routes.py file

# ============================================================================
# ROUTE 1: CREATE A NEW FILE
# ============================================================================
from ..repository.routes import *

@repo_routes.route("/create_file", methods=["POST"])
def create_file():
    """
    Creates a new file in the repository
    
    Expected JSON body:
    {
        "repo_id": "507f1f77bcf86cd799439011",
        "file_name": "main.py",
        "language": "python",
        "content": "print('Hello')"
    }
    """
    logger.info("File creation requested")
    
    # TODO 1: Check if user is authenticated with GitHub
    # - Use: if not github.authorized:
    # - Return JSON error with 401 status if not authenticated
    
    
    # TODO 2: Get the request JSON data
    # - Use: data = request.get_json()
    # - Extract: repo_id, file_name, language, content from data
    # - Use .get() method with defaults for optional fields
    
    
    # TODO 3: Validate required fields
    # - Check if repo_id exists and is not empty
    # - Check if file_name exists and is not empty
    # - Return JSON error with 400 status if validation fails
    
    
    # TODO 4: Get the authenticated GitHub user information
    # - Use: user_resp = github.get("/user")
    # - Check if response is ok: if not user_resp.ok:
    # - Extract username: github_username = user_resp.json()["login"]
    # - Handle errors with try/except
    
    
    # TODO 5: Find the user in the database
    # - Use: user_doc = user_collection.find_one({"username": github_username})
    # - Check if user exists, return 404 error if not found
    
    
    # TODO 6: Convert repo_id string to ObjectId
    # - Use: from bson import ObjectId
    # - Convert: repo_obj_id = ObjectId(repo_id)
    # - Wrap in try/except to catch invalid ObjectId format
    
    
    # TODO 7: Find the repository in database
    # - Use: repo_doc = repositories_collection.find_one({...})
    # - Query conditions: "_id" matches repo_obj_id AND "user_id" matches user_doc["_id"]
    # - This ensures the user owns the repository
    # - Return 404 error if repo not found
    
    
    # TODO 8: Check if file already exists in this repository
    # - Use: existing_file = files_collection.find_one({...})
    # - Query conditions: "repo_id" matches repo_doc["_id"] AND "path" matches file_name
    # - Return 409 (conflict) error if file already exists
    
    
    # TODO 9: Create the file document structure
    # - Create a dictionary with these fields:
    #   * "repo_id": repo_doc["_id"]
    #   * "user_id": user_doc["_id"]
    #   * "path": file_name (the file path/name)
    #   * "language": language (from request)
    #   * "content": content (from request, default to empty string if not provided)
    #   * "created_at": datetime.datetime.utcnow()
    #   * "updated_at": datetime.datetime.utcnow()
    
    
    # TODO 10: Insert the file into the database
    # - Use: insert_result = files_collection.insert_one(file_doc)
    # - Get the inserted ID: insert_result.inserted_id
    
    
    # TODO 11: Fetch the newly created file from database
    # - Use: saved_file = files_collection.find_one({"_id": insert_result.inserted_id})
    # - This ensures we get the complete document with all fields
    
    
    # TODO 12: Serialize the file document (convert ObjectId to string)
    # - Use the serialize_doc() helper function (already exists in your code)
    # - Convert: saved_file_serialized = serialize_doc(saved_file)
    
    
    # TODO 13: Return success response
    # - Return JSON with:
    #   * "message": success message
    #   * "file": the serialized file document
    # - Use 201 status code (created)
    # - Format: return jsonify({...}), 201
    
    
    # TODO 14: Add error handling
    # - Wrap entire function in try/except
    # - Catch general Exception
    # - Log the error: logger.error(f"Error creating file: {e}")
    # - Return JSON error with 500 status


# ============================================================================
# ROUTE 2: GET ALL FILES FOR A REPOSITORY
# ============================================================================
@repo_routes.route("/get_files/<repo_id>", methods=["GET"])
def get_files(repo_id):
    """
    Retrieves all files for a given repository
    
    URL parameter:
    - repo_id: MongoDB ObjectId as string
    
    Returns:
    {
        "files": [
            {
                "id": "507f1f77bcf86cd799439011",
                "path": "main.py",
                "language": "python",
                "content": "print('Hello')"
            },
            ...
        ]
    }
    """
    logger.info(f"Fetching files for repository: {repo_id}")
    
    # TODO 1: Check if user is authenticated
    # - Use: if not github.authorized:
    # - Return JSON error with 401 status
    
    
    # TODO 2: Convert repo_id to ObjectId
    # - Use: repo_obj_id = ObjectId(repo_id)
    # - Wrap in try/except to handle invalid ObjectId format
    # - Return 400 error if invalid
    
    
    # TODO 3: Get authenticated user information
    # - Use: user_resp = github.get("/user")
    # - Check response is ok
    # - Extract username
    
    
    # TODO 4: Find user in database
    # - Query user_collection by username
    # - Return 404 if not found
    
    
    # TODO 5: Verify repository exists and belongs to user
    # - Use: repo_doc = repositories_collection.find_one({...})
    # - Query: "_id" matches repo_obj_id AND "user_id" matches user_doc["_id"]
    # - Return 404 if repo not found or doesn't belong to user
    
    
    # TODO 6: Fetch all files for this repository
    # - Use: files_cursor = files_collection.find({"repo_id": repo_doc["_id"]})
    # - Convert cursor to list: list(files_cursor)
    # - Sort files by path for better organization (optional)
    
    
    # TODO 7: Serialize all file documents
    # - Loop through files list
    # - For each file, convert ObjectId fields to strings
    # - Create a list of dictionaries with:
    #   * "id": str(file["_id"])
    #   * "path": file["path"]
    #   * "language": file["language"]
    #   * "content": file["content"]
    
    
    # TODO 8: Return the files list
    # - Return JSON: {"files": serialized_files_list}
    # - Use 200 status code (default)
    
    
    # TODO 9: Add error handling
    # - Wrap in try/except
    # - Log errors
    # - Return 500 error with error message


# ============================================================================
# ROUTE 3 (OPTIONAL): UPDATE FILE CONTENT
# ============================================================================
@repo_routes.route("/update_file", methods=["PUT"])
def update_file():
    """
    Updates the content of an existing file
    
    Expected JSON body:
    {
        "file_id": "507f1f77bcf86cd799439011",
        "content": "print('Updated content')"
    }
    """
    logger.info("File update requested")
    
    # TODO 1: Check authentication
    
    
    # TODO 2: Get request data (file_id, content)
    
    
    # TODO 3: Validate required fields
    
    
    # TODO 4: Get authenticated user
    
    
    # TODO 5: Find user in database
    
    
    # TODO 6: Convert file_id to ObjectId
    
    
    # TODO 7: Find the file and verify ownership
    # - Query files_collection
    # - Check that file's user_id matches current user
    
    
    # TODO 8: Update the file content
    # - Use: files_collection.update_one(
    #     {"_id": file_obj_id},
    #     {"$set": {
    #         "content": content,
    #         "updated_at": datetime.datetime.utcnow()
    #     }}
    # )
    
    
    # TODO 9: Fetch updated file
    
    
    # TODO 10: Serialize and return
    
    
    # TODO 11: Error handling


# ============================================================================
# ROUTE 4 (OPTIONAL): DELETE FILE
# ============================================================================
@repo_routes.route("/delete_file/<file_id>", methods=["DELETE"])
def delete_file(file_id):
    """
    Deletes a file from the repository
    
    URL parameter:
    - file_id: MongoDB ObjectId as string
    """
    logger.info(f"File deletion requested: {file_id}")
    
    # TODO 1: Check authentication
    
    
    # TODO 2: Get authenticated user
    
    
    # TODO 3: Find user in database
    
    
    # TODO 4: Convert file_id to ObjectId
    
    
    # TODO 5: Find the file and verify ownership
    # - Query files_collection
    # - Verify user_id matches
    
    
    # TODO 6: Delete the file
    # - Use: delete_result = files_collection.delete_one({"_id": file_obj_id})
    # - Check: delete_result.deleted_count > 0
    
    
    # TODO 7: Return success response
    # - Return: {"message": "File deleted successfully"}
    
    
    # TODO 8: Error handling


# ============================================================================
# HELPER NOTES
# ============================================================================
"""
DATABASE COLLECTIONS YOU'LL USE:
- user_collection: stores user information
- repositories_collection: stores repository information  
- files_collection: stores file information

IMPORTANT IMPORTS NEEDED:
from bson import ObjectId
import datetime

ERROR HANDLING PATTERN:
try:
    # Your code here
    return jsonify({"data": result}), 200
except Exception as e:
    logger.error(f"Error: {e}")
    return jsonify({"error": str(e)}), 500

AUTHENTICATION CHECK:
if not github.authorized:
    return jsonify({"message": "Not authenticated"}), 401

SERIALIZATION:
- Use the serialize_doc() function that already exists
- It converts ObjectId to string for JSON response

LOGGING:
- Use logger.info() for normal operations
- Use logger.error() for errors

RESPONSE FORMAT:
- Success: return jsonify({...}), STATUS_CODE
- Error: return jsonify({"error": "message"}), STATUS_CODE

STATUS CODES:
- 200: OK (success)
- 201: Created (new resource)
- 400: Bad Request (validation error)
- 401: Unauthorized (not authenticated)
- 404: Not Found (resource doesn't exist)
- 409: Conflict (resource already exists)
- 500: Internal Server Error (unexpected error)
"""