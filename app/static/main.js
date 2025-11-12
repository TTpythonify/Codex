// Modal functionality
const createRepoBtn = document.getElementById('createRepoBtn');
const createRepoModal = document.getElementById('createRepoModal');
const closeModal = document.getElementById('closeModal');
const cancelBtn = document.getElementById('cancelBtn');
const createRepoForm = document.getElementById('createRepoForm');

// Open modal
if (createRepoBtn) {
    createRepoBtn.addEventListener('click', function() {
        if (createRepoModal) {
            createRepoModal.classList.add('active');
        }
    });
}

// Close modal functions
function closeModalFunc() {
    if (createRepoModal) {
        createRepoModal.classList.remove('active');
    }
}

if (closeModal) {
    closeModal.addEventListener('click', closeModalFunc);
}

if (cancelBtn) {
    cancelBtn.addEventListener('click', closeModalFunc);
}

// Close modal when clicking outside - FIXED: Check if modal exists
if (createRepoModal) {
    createRepoModal.addEventListener('click', function(e) {
        if (e.target === createRepoModal) {
            closeModalFunc();
        }
    });
}

// Handle form submission
if (createRepoForm) {
    createRepoForm.addEventListener('submit', async function (e) {  // make function async
        e.preventDefault();
        
        const repoName = document.getElementById('repoName').value.trim();
        const repoDescription = document.getElementById('repoDescription').value.trim();
        const visibility = document.querySelector('input[name="repoVisibility"]:checked').value;

        console.log('Creating repository:', { repoName, repoDescription, visibility });
        
        const data = {
            name: repoName,
            description: repoDescription,
            private: visibility === "private"
        };

        try {
            const response = await fetch("/create_repo", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(data)
            });

            const result = await response.json();
            console.log("Response:", result);

            if (response.ok) {
                alert("✅ Repository created successfully!");
                createRepoForm.reset();
                closeModalFunc();
            } else {
                alert("❌ Error: " + (result.message || "Something went wrong."));
            }

        } catch (err) {
            console.error("Error creating repository:", err);
            alert("⚠️ An error occurred while creating the repository.");
        }
    });
}


// GitHub OAuth button functionality
document.addEventListener('DOMContentLoaded', function() {
    const githubBtn = document.getElementById('githubLoginBtn');
    
    if (githubBtn) {
        githubBtn.addEventListener('click', function(e) {
            e.preventDefault();
            
            console.log('GitHub login button clicked');
            
            // Direct redirect to GitHub OAuth
            window.location.href = '/login/github';
            
            // Alternative: If you need to test the endpoint first
            /*
            fetch('/test-oauth')
                .then(response => response.json())
                .then(data => {
                    console.log('OAuth test response:', data);
                    if (data.status === 'success') {
                        window.location.href = '/login/github';
                    } else {
                        console.error('OAuth setup error:', data);
                        alert('OAuth setup error. Please check the console.');
                    }
                })
                .catch(error => {
                    console.error('Error connecting to OAuth:', error);
                    alert('Error connecting to OAuth. Please try again.');
                });
            */
        });
        
        console.log('GitHub login button event listener attached');
    } else {
        console.warn('GitHub login button not found on this page');
    }
});

// Project item click handlers
const projectItems = document.querySelectorAll('.project-item');
if (projectItems.length > 0) {
    projectItems.forEach(item => {
        item.addEventListener('click', function() {
            projectItems.forEach(p => p.classList.remove('active'));
            this.classList.add('active');
            
            const projectId = this.getAttribute('data-project-id');
            console.log('Selected project:', projectId);
            
            // Here you would load the project data
        });
    });
}

// Repo card click handlers
const repoCards = document.querySelectorAll('.repo-card');
if (repoCards.length > 0) {
    repoCards.forEach(card => {
        card.addEventListener('click', function() {
            const repoId = this.getAttribute('data-repo-id');
            console.log('Selected repository:', repoId);
            
            // Here you would navigate to the repository page
            // window.location.href = `/repository/${repoId}`;
        });
    });
}

console.log('Home page JavaScript loaded successfully');