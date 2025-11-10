document.addEventListener('DOMContentLoaded', function() {
    
    const githubBtn = document.getElementById('githubLoginBtn');
    
    if (githubBtn) {
        
        githubBtn.addEventListener('click', function(e) {
            
            // First, test if the OAuth route exists
            fetch('/test-oauth')
                .then(response => response.json())
                .then(data => {
                    
                    if (data.status === 'success') {
                        // Redirect to the OAuth URL
                        window.location.href = '/login/github';
                    } else {
                        alert("OAuth setup error. Check console for details.");
                    }
                })
                .catch(error => {
                    alert("Error connecting to OAuth. Check console.");
                });
        });
    } else {
        console.error("❌ GitHub button NOT found!");
    }
});

// Log when page is fully loaded
window.addEventListener('load', function() {
});