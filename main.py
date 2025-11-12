from app import create_app

app = create_app()


if __name__ == "__main__":
    if not app.secret_key:
        raise ValueError("FLASK_SECRET_KEY environment variable is required")
    app.run(debug=True, host="0.0.0.0", port=5000)