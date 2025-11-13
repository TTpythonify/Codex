# sandbox/sandbox_service.py
import tempfile
import subprocess
import uuid
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow backend to talk to sandbox over Docker network
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to backend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run")
async def run_code(req: Request):
    data = await req.json()
    code = data.get("code", "")

    if not code.strip():
        return {"output": "No code provided."}

    # Create a temporary file inside the sandbox container
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp_file:
        tmp_file.write(code)
        tmp_file_path = tmp_file.name

    container_name = f"sandbox_{uuid.uuid4().hex[:8]}"

    try:
        # Run code inside an ephemeral Docker container
        cmd = [
            "docker", "run", "--rm",
            "--name", container_name,
            "--network=none",          # No internet access
            "--memory=128m",           # Limit memory
            "--cpus=0.5",              # Limit CPU
            "-v", f"{tmp_file_path}:/sandbox/main.py:ro",
            "python:3.11-slim",
            "python3", "/sandbox/main.py"
        ]
        output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=5)
        result = output.decode("utf-8")

    except subprocess.CalledProcessError as e:
        result = e.output.decode("utf-8")
    except subprocess.TimeoutExpired:
        result = "Error: Code execution timed out."
    except Exception as ex:
        result = f"Unexpected error: {str(ex)}"
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

    return {"output": result}
