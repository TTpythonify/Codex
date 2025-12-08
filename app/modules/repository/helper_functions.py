import re

def to_java_class_name(filename):
    # remove .java if user included it
    if filename.endswith(".java"):
        filename = filename[:-5]

    # split by any non-alphanumeric character
    parts = re.split(r'[^a-zA-Z0-9]+', filename)

    # Capitalize each chunk
    parts = [p.capitalize() for p in parts if p]

    return "".join(parts)


