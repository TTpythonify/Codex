// Get the GitHub login button
const githubLoginBtn = document.getElementById('githubLoginBtn');

// Add click event listener
githubLoginBtn.addEventListener('click', handleGitHubLogin);

/**
 * Handles GitHub OAuth login flow
 * This function will be connected to your backend OAuth endpoint
 */
function handleGitHubLogin() {
    // Log the login attempt
    console.log('GitHub login initiated');
    
    // TODO: Replace with your actual backend OAuth endpoint
    // Example: window.location.href = '/auth/github';
    
    // For now, show an alert (remove this when implementing backend)
    alert('GitHub login will be connected to your backend OAuth flow');
    
    // Optional: Add loading state to button
    // githubLoginBtn.disabled = true;
    // githubLoginBtn.textContent = 'Connecting...';
}

/**
 * Optional: Handle OAuth callback
 * If GitHub redirects back to your page with code/token parameters
 */
function handleOAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    const error = urlParams.get('error');
    
    if (error) {
        console.error('OAuth error:', error);
        alert('Authentication failed. Please try again.');
        return;
    }
    
    if (code) {
        console.log('OAuth code received:', code);
        // Send code to your backend for token exchange
        // Example: fetch('/auth/github/callback?code=' + code)
    }
}

// Check for OAuth callback on page load
window.addEventListener('load', handleOAuthCallback);