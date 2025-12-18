import re
import redis
import bson


redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True
)


def convert_objectids(obj):
    """Recursively convert all ObjectIds in a dict/list to strings."""
    if isinstance(obj, list):
        return [convert_objectids(o) for o in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectids(v) for k, v in obj.items()}
    elif isinstance(obj, bson.ObjectId):
        return str(obj)
    else:
        return obj


def to_java_class_name(filename):
    # remove .java if user included it
    if filename.endswith(".java"):
        filename = filename[:-5]

    # split by any non-alphanumeric character
    parts = re.split(r'[^a-zA-Z0-9]+', filename)

    # Capitalize each chunk
    parts = [p.capitalize() for p in parts if p]

    return "".join(parts)




