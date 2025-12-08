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

    window.addEventListener('click', (e) => {
        if (e.target === createRepoModal) {
            createRepoModal.style.display = 'none';
            createRepoForm.reset();
        }
    });

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

    addRepoClickHandlers();
    addSidebarClickHandlers();
    initializeNotifications();
});

// Function to add a new repository card to the grid
function addRepoToGrid(repo) {
    const reposGrid = document.getElementById('reposGrid');
    
    // Remove "No Repositories Yet" card if exists
    const noReposCard = reposGrid.querySelector('[data-repo-id="0"]');
    if (noReposCard) noReposCard.remove();

    // Create new repo card
    const repoCard = document.createElement('div');
    repoCard.className = 'repo-card';
    repoCard.setAttribute('data-repo-id', repo._id);
    repoCard.setAttribute('data-is-owner', repo.is_owner ? 'true' : 'false');
    repoCard.setAttribute('data-members', JSON.stringify(repo.members || []));
    repoCard.style.cursor = 'pointer';

    repoCard.innerHTML = `
        <div class="repo-header">
            <svg class="repo-icon" width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z"/>
            </svg>
            <h3 class="repo-name">${repo.name}</h3>
            ${repo.is_owner ? '<span class="badge owner-badge">Owner</span>' : '<span class="badge member-badge">Member</span>'}
        </div>
        <p class="repo-description">${repo.description || 'No description provided'}</p>
        <div class="repo-footer">
            <div class="repo-stats">
                <span class="stat">${repo.private ? '🔒 Private' : '🔓 Public'}</span>
            </div>
            <span class="repo-time">${repo.created_at}</span>
        </div>
    `;

    // Add click handler
    repoCard.addEventListener('click', () => {
        const isOwner = repoCard.getAttribute('data-is-owner') === 'true';
        const members = JSON.parse(repoCard.getAttribute('data-members') || '[]');
        const currentGithubId = window.currentGithubId;

        console.log('Repo clicked:', repo.name);
        console.log('Is owner:', isOwner);
        console.log('Members array:', members);
        console.log('Current GitHub ID:', currentGithubId);
        console.log('Has access:', isOwner || members.includes(currentGithubId));

        // If you see the repo on this page, you have access (it was filtered server-side)
        // So we can just navigate directly
        window.location.href = `/repo/${repo._id}`;
    });

    reposGrid.appendChild(repoCard);
}


function addRepoClickHandlers() {
    const repoCards = document.querySelectorAll('.repo-card');
    repoCards.forEach(card => {
        const repoId = card.getAttribute('data-repo-id');
        const isOwner = card.getAttribute('data-is-owner') === 'true';
        const members = JSON.parse(card.getAttribute('data-members') || '[]');
        const currentGithubId = window.currentGithubId;

        console.log('Setting up click handler for repo:', repoId);
        console.log('Is owner:', isOwner);
        console.log('Members:', members);
        console.log('Current GitHub ID:', currentGithubId);

        if (repoId && repoId !== '0') {
            card.style.cursor = 'pointer';
            card.addEventListener('click', () => {
                console.log('Repo card clicked:', repoId);
                console.log('Checking access...');
                console.log('Is owner:', isOwner);
                console.log('Members includes user:', members.includes(currentGithubId));
                
                // Since the server already filtered repos to only show ones the user has access to,
                // we can safely navigate without additional checks
                window.location.href = `/repo/${repoId}`;
            });
        }
    });
}


// Add click handlers for sidebar project items
function addSidebarClickHandlers() {
    const projectItems = document.querySelectorAll('.project-item');
    projectItems.forEach(item => {
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => {
            const projectId = item.getAttribute('data-project-id');
            switch (projectId) {
                case '1': // My Project
                    window.location.href = '/home';
                    break;
                case '2': // Public Repositories
                    window.location.href = '/public_repositories';
                    break;
                case '3': // Activity Feeds
                    window.location.href = '/activity_feed';
                    break;
                default:
                    console.warn('Unknown project item clicked');
            }
        });

        // Keyboard accessibility (Enter/Space)
        item.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                item.click();
            }
        });
    });
}


async function loadRecentActivities() {
    const activityList = document.getElementById('recentActivityList');
    if (!activityList) return;
    
    try {
        const response = await fetch('/get_activities?limit=5');
        const data = await response.json();
        
        if (response.ok && data.activities && data.activities.length > 0) {
            activityList.innerHTML = '';
            
            data.activities.forEach(activity => {
                const activityElement = createHomeActivityElement(activity);
                activityList.appendChild(activityElement);
            });
        } else {
            activityList.innerHTML = `
                <div class="activity-empty">
                    <svg width="48" height="48" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M1.5 1.75V13.5h13.75a.75.75 0 010 1.5H.75a.75.75 0 01-.75-.75V1.75a.75.75 0 011.5 0zm14.28 2.53l-5.25 5.25a.75.75 0 01-1.06 0L7 7.06 4.28 9.78a.75.75 0 01-1.06-1.06l3.25-3.25a.75.75 0 011.06 0L10 7.94l4.72-4.72a.75.75 0 111.06 1.06z"/>
                    </svg>
                    <h4>No Recent Activity</h4>
                    <p>Start creating repositories and files to see your activity here</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('Error loading recent activities:', error);
        activityList.innerHTML = `
            <div class="activity-empty">
                <h4>Unable to load activities</h4>
                <p>Please refresh the page to try again</p>
            </div>
        `;
    }
}

function createHomeActivityElement(activity) {
    const div = document.createElement('div');
    div.className = 'activity-item';
    
    // Determine icon class
    let iconClass = 'edit';
    let icon = '';
    
    switch(activity.type) {
        case 'create_repo':
            iconClass = 'create';
            icon = `<svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z"/>
            </svg>`;
            break;
        case 'create_file':
            iconClass = 'commit';
            icon = `<svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0113.25 16h-9.5A1.75 1.75 0 012 14.25V1.75z"/>
            </svg>`;
            break;
        case 'run_code':
            iconClass = 'edit';
            icon = `<svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4.72 3.22a.75.75 0 011.06 1.06L2.06 8l3.72 3.72a.75.75 0 11-1.06 1.06L.47 8.53a.75.75 0 010-1.06l4.25-4.25zm6.56 0a.75.75 0 10-1.06 1.06L13.94 8l-3.72 3.72a.75.75 0 101.06 1.06l4.25-4.25a.75.75 0 000-1.06l-4.25-4.25z"/>
            </svg>`;
            break;
        case 'create_folder':
            iconClass = 'folder';
            icon = `<svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M1.75 1A1.75 1.75 0 000 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0016 13.25v-8.5A1.75 1.75 0 0014.25 3H7.5a.25.25 0 01-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1H1.75z"/>
            </svg>`;
            break;
    }
    
    div.innerHTML = `
        <div class="activity-icon ${iconClass}">
            ${icon}
        </div>
        <div class="activity-content">
            <h4>${activity.title}</h4>
            <p>${activity.description}</p>
        </div>
    `;
    
    // Make clickable if has repo_id
    if (activity.repo_id) {
        div.addEventListener('click', () => {
            window.location.href = `/repo/${activity.repo_id}`;
        });
    }
    
    return div;
}

// Load activities when page loads
if (document.getElementById('recentActivityList')) {
    loadRecentActivities();
}

// ==========================================
// NOTIFICATION BELL FUNCTIONALITY
// ==========================================

function initializeNotifications() {
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationDropdown = document.getElementById('notificationDropdown');
    const notificationBadge = document.getElementById('notificationBadge');
    const markAllRead = document.getElementById('markAllRead');
    
    if (!notificationBtn) return;
    
    // Toggle notification dropdown
    notificationBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        notificationDropdown.classList.toggle('active');
        notificationBtn.classList.toggle('active');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!notificationBtn.contains(e.target) && !notificationDropdown.contains(e.target)) {
            notificationDropdown.classList.remove('active');
            notificationBtn.classList.remove('active');
        }
    });
    
    // Mark all as read
    if (markAllRead) {
        markAllRead.addEventListener('click', () => {
            markAllNotificationsAsRead();
        });
    }
    
    // Add click handlers to notification items
    const notificationItems = document.querySelectorAll('.notification-item');
    notificationItems.forEach(item => {
        item.addEventListener('click', () => {
            markNotificationAsRead(item);
            // You can add navigation logic here
        });
    });
}

function markAllNotificationsAsRead() {
    const notificationItems = document.querySelectorAll('.notification-item.unread');
    notificationItems.forEach(item => {
        item.classList.remove('unread');
    });
    updateNotificationBadge();
    
    // TODO: Send request to backend to mark all as read
    // fetch('/notifications/mark_all_read', { method: 'POST' })
    //     .then(response => response.json())
    //     .then(data => console.log('All notifications marked as read'))
    //     .catch(error => console.error('Error:', error));
}

function markNotificationAsRead(notificationItem) {
    notificationItem.classList.remove('unread');
    updateNotificationBadge();
    
    // TODO: Send request to backend to mark specific notification as read
    // const notificationId = notificationItem.dataset.notificationId;
    // fetch(`/notifications/${notificationId}/read`, { method: 'POST' })
    //     .then(response => response.json())
    //     .then(data => console.log('Notification marked as read'))
    //     .catch(error => console.error('Error:', error));
}

function updateNotificationBadge() {
    const notificationBadge = document.getElementById('notificationBadge');
    if (!notificationBadge) return;
    
    const unreadCount = document.querySelectorAll('.notification-item.unread').length;
    
    if (unreadCount > 0) {
        notificationBadge.textContent = unreadCount > 99 ? '99+' : unreadCount;
        notificationBadge.classList.remove('hidden');
    } else {
        notificationBadge.classList.add('hidden');
    }
}

// Function to add a new notification dynamically (you can call this from your backend)
function addNotification(notification) {
    const notificationList = document.getElementById('notificationList');
    if (!notificationList) return;
    
    // Remove empty state if exists
    const emptyState = notificationList.querySelector('.notification-empty');
    if (emptyState) {
        emptyState.remove();
    }
    
    const notificationItem = document.createElement('div');
    notificationItem.className = 'notification-item unread';
    if (notification.id) {
        notificationItem.dataset.notificationId = notification.id;
    }
    
    // Determine icon based on notification type
    let iconClass = 'file';
    let iconSvg = `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
        <path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0113.25 16h-9.5A1.75 1.75 0 012 14.25V1.75z"/>
    </svg>`;
    
    if (notification.type === 'member') {
        iconClass = 'new-member';
        iconSvg = `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M10.5 5a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zm.061 3.073a4 4 0 10-5.123 0 6.004 6.004 0 00-3.431 5.142.75.75 0 001.498.07 4.5 4.5 0 018.99 0 .75.75 0 101.498-.07 6.005 6.005 0 00-3.432-5.142z"/>
        </svg>`;
    } else if (notification.type === 'commit') {
        iconClass = 'commit';
        iconSvg = `<svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M11.93 8.5a4.002 4.002 0 01-7.86 0H.75a.75.75 0 010-1.5h3.32a4.002 4.002 0 017.86 0h3.32a.75.75 0 010 1.5h-3.32zM8 6a2 2 0 100 4 2 2 0 000-4z"/>
        </svg>`;
    }
    
    notificationItem.innerHTML = `
        <div class="notification-icon ${iconClass}">
            ${iconSvg}
        </div>
        <div class="notification-content">
            <p>${notification.message}</p>
            <span class="notification-time">${notification.time}</span>
        </div>
    `;
    
    // Add click handler
    notificationItem.addEventListener('click', () => {
        markNotificationAsRead(notificationItem);
    });
    
    // Insert at the top of the list
    notificationList.insertBefore(notificationItem, notificationList.firstChild);
    
    // Update badge
    updateNotificationBadge();
}

// Function to load notifications from backend
async function loadNotifications() {
    try {
        // TODO: Replace with your actual endpoint
        // const response = await fetch('/api/notifications');
        // const data = await response.json();
        
        // Example: Process notifications
        // if (data.notifications) {
        //     const notificationList = document.getElementById('notificationList');
        //     notificationList.innerHTML = '';
        //     
        //     data.notifications.forEach(notification => {
        //         addNotification(notification);
        //     });
        //     
        //     updateNotificationBadge();
        // }
    } catch (error) {
        console.error('Error loading notifications:', error);
    }
}

// Example: Simulate receiving a notification (REMOVE THIS IN PRODUCTION)
// setTimeout(() => {
//     addNotification({
//         id: '123',
//         type: 'member',
//         message: '<strong>Alice</strong> joined <strong>Your Project</strong>',
//         time: 'Just now'
//     });
// }, 3000);