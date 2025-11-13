console.log("I am here ")
// GitHub Login Button Handler
document.addEventListener('DOMContentLoaded', () => {
    const githubLoginBtn = document.getElementById('githubLoginBtn');
    if (githubLoginBtn) {
        githubLoginBtn.addEventListener('click', async () => {
            try {
                window.location.href = '/login/github';
            } catch (error) {
                console.error('Error during GitHub login:', error);
                alert('Failed to initiate GitHub login. Please try again.');
            }
        });
    }

    // Modal functionality
    const createRepoBtn = document.getElementById('createRepoBtn');
    const createRepoModal = document.getElementById('createRepoModal');
    const closeModal = document.getElementById('closeModal');
    const cancelBtn = document.getElementById('cancelBtn');
    const createRepoForm = document.getElementById('createRepoForm');

    if (createRepoBtn) {
        createRepoBtn.addEventListener('click', () => {
            createRepoModal.style.display = 'flex';
        });
    }

    if (closeModal) {
        closeModal.addEventListener('click', () => {
            createRepoModal.style.display = 'none';
            createRepoForm.reset();
        });
    }

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            createRepoModal.style.display = 'none';
            createRepoForm.reset();
        });
    }

    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === createRepoModal) {
            createRepoModal.style.display = 'none';
            createRepoForm.reset();
        }
    });

    // Handle form submission
    if (createRepoForm) {
        createRepoForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const repoName = document.getElementById('repoName').value;
            const repoDescription = document.getElementById('repoDescription').value;
            const repoVisibility = document.querySelector('input[name="repoVisibility"]:checked').value;

            const submitButton = createRepoForm.querySelector('button[type="submit"]');
            submitButton.disabled = true;
            submitButton.textContent = 'Creating...';

            try {
                const response = await fetch('/create_repo', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        name: repoName,
                        description: repoDescription,
                        private: repoVisibility === 'private'
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    alert('Repository created successfully!');
                    createRepoModal.style.display = 'none';
                    createRepoForm.reset();
                    
                    // Add the new repository to the grid immediately
                    addRepoToGrid(data.repo);
                } else {
                    alert(`Failed to create repository: ${data.message}`);
                }
            } catch (error) {
                console.error('Error creating repository:', error);
                alert('An error occurred while creating the repository.');
            } finally {
                submitButton.disabled = false;
                submitButton.textContent = 'Create Repository';
            }
        });
    }

    // Add click handlers to existing repo cards
    addRepoClickHandlers();
});

// Function to add a new repository card to the grid
function addRepoToGrid(repo) {
    const reposGrid = document.getElementById('reposGrid');
    
    // Remove "No Repositories Yet" card if it exists
    const noReposCard = reposGrid.querySelector('[data-repo-id="4"]');
    if (noReposCard) {
        noReposCard.remove();
    }

    // Create new repo card
    const repoCard = document.createElement('div');
    repoCard.className = 'repo-card';
    repoCard.setAttribute('data-repo-id', repo.id);
    repoCard.style.cursor = 'pointer';
    
    repoCard.innerHTML = `
        <div class="repo-header">
            <svg class="repo-icon" width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z"/>
            </svg>
            <h3 class="repo-name">${repo.name}</h3>
        </div>
        <p class="repo-description">${repo.description || 'No description provided'}</p>
        <div class="repo-footer">
            <div class="repo-stats">
                <span class="stat">
                    ${repo.private ? '🔒 Private' : '🔓 Public'}
                </span>
            </div>
            <span class="repo-time">${repo.created_at}</span>
        </div>
    `;
    
    // Add click handler to navigate to repo page
    repoCard.addEventListener('click', () => {
        window.location.href = `/repo/${repo.id}`;
    });
    
    reposGrid.appendChild(repoCard);
}

// Function to add click handlers to existing repo cards
function addRepoClickHandlers() {
    const repoCards = document.querySelectorAll('.repo-card');
    repoCards.forEach(card => {
        const repoId = card.getAttribute('data-repo-id');
        // Don't add handler to the "No Repositories Yet" card
        if (repoId && repoId !== '4') {
            card.style.cursor = 'pointer';
            card.addEventListener('click', () => {
                window.location.href = `/repo/${repoId}`;
            });
        }
    });
}