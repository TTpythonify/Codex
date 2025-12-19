from app import create_app
from werkzeug.middleware.proxy_fix import ProxyFix

app = create_app()

# Add this to fix HTTPS URLs behind Railway proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config["PREFERRED_URL_SCHEME"] = "https"

if __name__ == "__main__":
    if not app.secret_key:
        raise ValueError("FLASK_SECRET_KEY environment variable is required")
    
    app.run(debug=True, host="0.0.0.0", port=5000)
