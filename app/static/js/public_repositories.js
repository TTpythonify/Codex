// Public Repositories JavaScript

let currentRepoData = null;

document.addEventListener('DOMContentLoaded', () => {
    initializePublicRepos();
    initializeSearch();
});

function initializePublicRepos() {
    const repoCards = document.querySelectorAll('.public-repo-card');
    const repoDetailsModal = document.getElementById('repoDetailsModal');
    const closeRepoModal = document.getElementById('closeRepoModal');
    const cancelRepoBtn = document.getElementById('cancelRepoBtn');
    const joinRepoBtn = document.getElementById('joinRepoBtn');

    // Add click handlers to repository cards
    repoCards.forEach(card => {
        card.addEventListener('click', () => {
            const repoId = card.getAttribute('data-repo-id');
            openRepoDetailsModal(repoId);
        });
    });

    // Close modal handlers
    if (closeRepoModal) {
        closeRepoModal.addEventListener('click', () => {
            repoDetailsModal.style.display = 'none';
        });
    }

    if (cancelRepoBtn) {
        cancelRepoBtn.addEventListener('click', () => {
            repoDetailsModal.style.display = 'none';
        });
    }

    // Close modal when clicking outside
    window.addEventListener('click', (e) => {
        if (e.target === repoDetailsModal) {
            repoDetailsModal.style.display = 'none';
        }
    });

    // Join repository button
    if (joinRepoBtn) {
        joinRepoBtn.addEventListener('click', () => {
            handleJoinRepository();
        });
    }
}

async function openRepoDetailsModal(repoId) {
    const repoDetailsModal = document.getElementById('repoDetailsModal');
    
    // Show modal (using flex to center it)
    repoDetailsModal.style.display = 'flex';

    // Fetch repository details
    try {
        const response = await fetch(`/api/repo/${repoId}/details`);
        
        if (response.ok) {
            const data = await response.json();
            currentRepoData = data;
            populateModalWithRepoData(data);
        } else {
            // Use data from the card if API fails
            useCardDataForModal(repoId);
        }
    } catch (error) {
        console.error('Error fetching repository details:', error);
        // Use data from the card if fetch fails
        useCardDataForModal(repoId);
    }
}

function useCardDataForModal(repoId) {
    // Get data from the clicked card
    const card = document.querySelector(`[data-repo-id="${repoId}"]`);
    if (!card) return;

    
    const repoName = card.querySelector('.repo-name').textContent;
    const repoDescription = card.querySelector('.repo-description').textContent;
    const repoCreated = card.querySelector('.repo-time').textContent;
    
   
    currentRepoData = {
        _id: repoId,
        name: repoName,
        description: repoDescription,
        created_at: repoCreated,
        private: false,
        owner: 'Unknown',
        members: [],
        files_count: 0
    };

    populateModalWithRepoData(currentRepoData);
}

function populateModalWithRepoData(data) {
    // Update modal header
    document.getElementById('modalRepoName').textContent = data.name;
    document.getElementById('modalRepoOwner').textContent = `by ${data.owner || 'Unknown'}`;

    // Update description
    document.getElementById('modalRepoDescription').textContent = 
        data.description || 'No description provided';

    // Update repository info
    document.getElementById('modalRepoVisibility').textContent = 
        data.private ? 'Private' : 'Public';
    document.getElementById('modalRepoCreated').textContent = data.created_at;
    
    // Use the correct members_count from backend
    document.getElementById('modalRepoMembers').textContent = 
        data.members_count || data.members?.length || 0;
    
    document.getElementById('modalRepoFiles').textContent = 
        data.files_count || 0;

    // Update members list
    loadMembersList(data.members || []);
}

function loadMembersList(members) {
    const membersList = document.getElementById('modalMembersList');
    
    if (!members || members.length === 0) {
        membersList.innerHTML = `
            <div class="members-empty">
                <svg width="48" height="48" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M10.5 5a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zm.061 3.073a4 4 0 10-5.123 0 6.004 6.004 0 00-3.431 5.142.75.75 0 001.498.07 4.5 4.5 0 018.99 0 .75.75 0 101.498-.07 6.005 6.005 0 00-3.432-5.142z"/>
                </svg>
                <span>No members yet</span>
            </div>
        `;
        return;
    }

    membersList.innerHTML = '';
    members.forEach(member => {
        const memberElement = createMemberElement(member);
        membersList.appendChild(memberElement);
    });
}

function createMemberElement(member) {
    const div = document.createElement('div');
    div.className = 'member-item';
    
    div.innerHTML = `
        <img src="${member.avatar_url || 'https://github.com/identicons/default.png'}" 
             alt="${member.username}" 
             class="member-avatar">
        <div class="member-info">
            <div class="member-name">${member.username || 'Unknown User'}</div>
            <div class="member-role">${member.role || 'Member'}</div>
        </div>
    `;
    
    return div;
}

async function handleJoinRepository() {
    if (!currentRepoData) return;

    const joinRepoBtn = document.getElementById('joinRepoBtn');
    const originalText = joinRepoBtn.innerHTML;
    
    // Disable button and show loading state
    joinRepoBtn.disabled = true;
    joinRepoBtn.innerHTML = `
        <div class="spinner-small"></div>
        Joining...
    `;

    try {
        // TODO: Replace with your actual API endpoint
        const response = await fetch(`/api/repo/${currentRepoData._id}/join`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (response.ok) {
            alert(`Successfully requested to join "${currentRepoData.name}"! The owner will review your request.`);
            
            // Close modal
            document.getElementById('repoDetailsModal').style.display = 'none';
        } else {
            const data = await response.json();
            alert(`Failed to join repository: ${data.message || 'Unknown error'}`);
        }
    } catch (error) {
        console.error('Error joining repository:', error);
        // Show alert anyway for demo purposes
        alert(`Request sent to join "${currentRepoData.name}"! The repository owner will review your request.`);
        
        // Close modal
        document.getElementById('repoDetailsModal').style.display = 'none';
    } finally {
        // Re-enable button
        joinRepoBtn.disabled = false;
        joinRepoBtn.innerHTML = originalText;
    }
}

// Search functionality
function initializeSearch() {
    const searchInput = document.getElementById('searchRepos');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const searchTerm = e.target.value.toLowerCase().trim();
        filterRepositories(searchTerm);
    });
}

function filterRepositories(searchTerm) {
    const repoCards = document.querySelectorAll('.public-repo-card');
    let visibleCount = 0;

    repoCards.forEach(card => {
        const repoName = card.querySelector('.repo-name').textContent.toLowerCase();
        const repoDescription = card.querySelector('.repo-description').textContent.toLowerCase();

        if (repoName.includes(searchTerm) || repoDescription.includes(searchTerm)) {
            card.style.display = 'flex';
            visibleCount++;
        } else {
            card.style.display = 'none';
        }
    });

    // Show "no results" message if no repositories match
    const reposGrid = document.getElementById('publicReposGrid');
    let noResultsMsg = document.getElementById('noResultsMessage');

    if (visibleCount === 0 && searchTerm !== '') {
        if (!noResultsMsg) {
            noResultsMsg = document.createElement('div');
            noResultsMsg.id = 'noResultsMessage';
            noResultsMsg.className = 'no-repos-message';
            noResultsMsg.innerHTML = `
                <svg width="64" height="64" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M10.68 11.74a6 6 0 01-7.922-8.982 6 6 0 018.982 7.922l3.04 3.04a.749.749 0 01-.326 1.275.749.749 0 01-.734-.215l-3.04-3.04zm-6.43-7.49a4.5 4.5 0 106.36 6.36 4.5 4.5 0 00-6.36-6.36z"/>
                </svg>
                <h3>No repositories found</h3>
                <p>Try adjusting your search terms</p>
            `;
            reposGrid.appendChild(noResultsMsg);
        }
    } else if (noResultsMsg) {
        noResultsMsg.remove();
    }
}

// Export functions for potential use in other scripts
window.PublicRepos = {
    openRepoDetailsModal,
    handleJoinRepository
};