from flask import Blueprint, render_template, redirect, url_for, session, jsonify
from flask_dance.contrib.github import github

main_routes = Blueprint("main", __name__)

# Home / login page
@main_routes.route("/")
def login_page():
    # If user already logged in via GitHub, redirect to home
    if github.authorized:
        try:
            resp = github.get("/user")
            if resp.ok:
                return redirect(url_for("main.home"))
        except:
            pass
    return render_template("login_page.html")

# Test route to check if OAuth URL is working
@main_routes.route("/test-oauth")
def test_oauth():
    try:
        # Try to get the OAuth URL
        from flask import url_for
        oauth_url = url_for('github.login', _external=True)
        return jsonify({
            "status": "success",
            "oauth_url": oauth_url,
            "message": "OAuth route exists!"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "error": str(e)
        })

# Home page (after successful login)
@main_routes.route("/home")
def home():
    if not github.authorized:
        return redirect(url_for("main.login_page"))
    
    try:
        resp = github.get("/user")
        if resp.ok:
            user_data = resp.json()
            print(f"\n{user_data}\n")
            return render_template("home_page.html", user=user_data)
    except Exception as e:
        print(f"Error fetching user data: {e}")
    
    return redirect(url_for("main.login_page"))

# Logout route
@main_routes.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("main.login_page"))

# Callback handler
@main_routes.route("/authorized")
def authorized():
    return redirect(url_for("main.home"))