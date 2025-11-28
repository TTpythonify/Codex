// Activity Feed JavaScript

let allActivities = [];
let currentFilter = 'all';

// Load activities on page load
document.addEventListener('DOMContentLoaded', () => {
    loadActivities();
    setupFilterButtons();
});

// Load activities from API
async function loadActivities() {
    const timeline = document.getElementById('activityTimeline');
    
    try {
        const response = await fetch('/get_activities?limit=50');
        const data = await response.json();
        
        if (response.ok && data.activities) {
            allActivities = data.activities;
            renderActivities(allActivities);
        } else {
            showEmptyState();
        }
    } catch (error) {
        console.error('Error loading activities:', error);
        showErrorState();
    }
}

// Setup filter buttons
function setupFilterButtons() {
    const filterButtons = document.querySelectorAll('.filter-btn');
    
    filterButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            // Update active state
            filterButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // Filter activities
            currentFilter = btn.dataset.filter;
            const filtered = currentFilter === 'all' 
                ? allActivities 
                : allActivities.filter(a => a.type === currentFilter);
            
            renderActivities(filtered);
        });
    });
}

// Render activities with date grouping
function renderActivities(activities) {
    const timeline = document.getElementById('activityTimeline');
    timeline.innerHTML = '';
    
    if (activities.length === 0) {
        showEmptyState();
        return;
    }
    
    // Group activities by date
    const groupedByDate = groupActivitiesByDate(activities);
    
    // Render each date group
    Object.keys(groupedByDate).forEach((date, index) => {
        // Add date divider (except for first one)
        if (index > 0) {
            const divider = createDateDivider(date);
            timeline.appendChild(divider);
        }
        
        // Render activities for this date
        groupedByDate[date].forEach(activity => {
            const activityElement = createActivityElement(activity);
            timeline.appendChild(activityElement);
        });
    });
}

// Group activities by date
function groupActivitiesByDate(activities) {
    const grouped = {};
    
    activities.forEach(activity => {
        const date = formatDateGroup(activity.timestamp);
        if (!grouped[date]) {
            grouped[date] = [];
        }
        grouped[date].push(activity);
    });
    
    return grouped;
}

// Format date for grouping (Today, Yesterday, date)
function formatDateGroup(timestamp) {
    if (!timestamp) return 'Unknown';
    
    const date = new Date(timestamp);
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (isSameDay(date, today)) {
        return 'Today';
    } else if (isSameDay(date, yesterday)) {
        return 'Yesterday';
    } else {
        return date.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
    }
}

// Check if two dates are the same day
function isSameDay(date1, date2) {
    return date1.getFullYear() === date2.getFullYear() &&
           date1.getMonth() === date2.getMonth() &&
           date1.getDate() === date2.getDate();
}

// Create date divider element
function createDateDivider(dateText) {
    const divider = document.createElement('div');
    divider.className = 'timeline-date-divider';
    divider.innerHTML = `
        <span class="date-divider-text">${dateText}</span>
        <div class="date-divider-line"></div>
    `;
    return divider;
}

// Create activity element
function createActivityElement(activity) {
    const item = document.createElement('div');
    item.className = `timeline-item ${activity.type}`;
    
    const icon = getActivityIcon(activity.type);
    const languageBadge = activity.language ? `<span class="activity-badge ${activity.language}">${activity.language}</span>` : '';
    
    const repoLink = activity.repo_id 
        ? `<a href="/repo/${activity.repo_id}" class="meta-item repo-link">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z"/>
            </svg>
            ${activity.repo_name || 'Repository'}
        </a>`
        : '';
    
    const fileName = activity.file_name 
        ? `<span class="meta-item">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0113.25 16h-9.5A1.75 1.75 0 012 14.25V1.75z"/>
            </svg>
            ${activity.file_name}
        </span>`
        : '';
    
    const metadataTags = renderMetadataTags(activity.metadata);
    
    item.innerHTML = `
        <div class="activity-card">
            <div class="activity-card-header">
                <div class="activity-type-icon ${activity.type}">
                    ${icon}
                </div>
                <div class="activity-card-info">
                    <div class="activity-card-title">
                        ${activity.title}
                        ${languageBadge}
                    </div>
                    <div class="activity-card-description">
                        ${activity.description}
                    </div>
                    <div class="activity-card-meta">
                        ${repoLink}
                        ${fileName}
                        <span class="meta-item">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                <path d="M8 0a8 8 0 110 16A8 8 0 018 0zM1.5 8a6.5 6.5 0 1113 0 6.5 6.5 0 01-13 0zm7-3.25v2.992l2.028.812a.75.75 0 01-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5a.75.75 0 011.5 0z"/>
                            </svg>
                            ${formatTimeAgo(activity.timestamp)}
                        </span>
                    </div>
                </div>
            </div>
            ${metadataTags ? `
                <div class="activity-card-footer">
                    <div class="metadata-tags">
                        ${metadataTags}
                    </div>
                </div>
            ` : ''}
        </div>
    `;
    
    // Add click handler if repo_id exists
    if (activity.repo_id) {
        item.style.cursor = 'pointer';
        item.addEventListener('click', () => {
            window.location.href = `/repo/${activity.repo_id}`;
        });
    }
    
    return item;
}

// Get activity icon based on type
function getActivityIcon(type) {
    const icons = {
        'create_repo': `<svg width="24" height="24" viewBox="0 0 16 16" fill="currentColor">
            <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z"/>
        </svg>`,
        'create_file': `<svg width="24" height="24" viewBox="0 0 16 16" fill="currentColor">
            <path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0113.25 16h-9.5A1.75 1.75 0 012 14.25V1.75z"/>
        </svg>`,
        'create_folder': `<svg width="24" height="24" viewBox="0 0 16 16" fill="currentColor">
            <path d="M1.75 1A1.75 1.75 0 000 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0016 13.25v-8.5A1.75 1.75 0 0014.25 3H7.5a.25.25 0 01-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1H1.75z"/>
        </svg>`,
        'run_code': `<svg width="24" height="24" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 4a4 4 0 100 8 4 4 0 000-8zM6 8l3-2v4L6 8z"/>
        </svg>`
    };
    return icons[type] || icons['create_file'];
}

// Render metadata tags
function renderMetadataTags(metadata) {
    if (!metadata || Object.keys(metadata).length === 0) return '';
    
    let tags = [];
    
    if (metadata.lines) {
        tags.push(`<span class="metadata-tag">${metadata.lines} lines</span>`);
    }
    
    if (metadata.private !== undefined) {
        tags.push(`<span class="metadata-tag">${metadata.private ? '🔒 Private' : '🔓 Public'}</span>`);
    }
    
    return tags.join('');
}

// Format time ago
function formatTimeAgo(timestamp) {
    if (!timestamp) return 'Unknown time';
    
    const date = new Date(timestamp);
    const now = new Date();
    const seconds = Math.floor((now - date) / 1000);
    
    const intervals = {
        year: 31536000,
        month: 2592000,
        week: 604800,
        day: 86400,
        hour: 3600,
        minute: 60,
        second: 1
    };
    
    for (const [unit, secondsInUnit] of Object.entries(intervals)) {
        const interval = Math.floor(seconds / secondsInUnit);
        if (interval >= 1) {
            return `${interval} ${unit}${interval !== 1 ? 's' : ''} ago`;
        }
    }
    
    return 'just now';
}

// Show empty state
function showEmptyState() {
    const timeline = document.getElementById('activityTimeline');
    timeline.innerHTML = `
        <div class="timeline-empty">
            <svg width="64" height="64" viewBox="0 0 16 16" fill="currentColor">
                <path d="M8 4a4 4 0 100 8 4 4 0 000-8z"/>
            </svg>
            <h3>No Activity Yet</h3>
            <p>Start creating repositories, files, or running code<br>to see your activity timeline here.</p>
        </div>
    `;
}

// Show error state
function showErrorState() {
    const timeline = document.getElementById('activityTimeline');
    timeline.innerHTML = `
        <div class="timeline-empty">
            <svg width="64" height="64" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2.343 13.657A8 8 0 1113.657 2.343 8 8 0 012.343 13.657zM6.03 4.97a.75.75 0 00-1.06 1.06L6.94 8 4.97 9.97a.75.75 0 101.06 1.06L8 9.06l1.97 1.97a.75.75 0 101.06-1.06L9.06 8l1.97-1.97a.75.75 0 10-1.06-1.06L8 6.94 6.03 4.97z"/>
            </svg>
            <h3>Failed to Load Activities</h3>
            <p>There was an error loading your activity feed.<br>Please try refreshing the page.</p>
        </div>
    `;
}