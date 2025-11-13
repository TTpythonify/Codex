FROM python:3.11-slim

WORKDIR /app

# Copy requirements from root context
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy sandbox folder contents
COPY sandbox/ ./

# Expose port for FastAPI
EXPOSE 8000

# Start FastAPI
CMD ["uvicorn", "sandbox_service:app", "--host", "0.0.0.0", "--port", "8000"]
