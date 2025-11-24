// Activity Feed JavaScript
let allActivities = [];
let currentFilter = 'all';

// Load activities on page load
document.addEventListener('DOMContentLoaded', () => {
    loadActivities();
    setupEventListeners();
});

function setupEventListeners() {
    // Filter chips
    const filterChips = document.querySelectorAll('.filter-chip');
    filterChips.forEach(chip => {
        chip.addEventListener('click', () => {
            // Update active state
            filterChips.forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            
            // Apply filter
            currentFilter = chip.dataset.filter;
            renderActivities();
        });
    });
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshActivities');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', () => {
            loadActivities();
        });
    }
}

async function loadActivities() {
    const loadingState = document.getElementById('loadingState');
    const emptyState = document.getElementById('emptyState');
    const timeline = document.getElementById('activityTimeline');
    
    // Show loading
    if (loadingState) loadingState.style.display = 'flex';
    if (emptyState) emptyState.style.display = 'none';
    if (timeline) timeline.innerHTML = '';
    
    try {
        const response = await fetch('/get_activities');
        const data = await response.json();
        
        if (response.ok) {
            allActivities = data.activities || [];
            
            // Hide loading
            if (loadingState) loadingState.style.display = 'none';
            
            // Update stats
            updateStats();
            
            // Render activities
            renderActivities();
        } else {
            throw new Error(data.error || 'Failed to load activities');
        }
    } catch (error) {
        console.error('Error loading activities:', error);
        if (loadingState) loadingState.style.display = 'none';
        if (emptyState) {
            emptyState.style.display = 'flex';
            emptyState.querySelector('h3').textContent = 'Error Loading Activities';
            emptyState.querySelector('p').textContent = 'Please try refreshing the page.';
        }
    }
}

function updateStats() {
    const totalActivitiesElem = document.getElementById('totalActivities');
    if (totalActivitiesElem) {
        const count = allActivities.length;
        totalActivitiesElem.innerHTML = `
            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                <path d="M1.5 1.75V13.5h13.75a.75.75 0 010 1.5H.75a.75.75 0 01-.75-.75V1.75a.75.75 0 011.5 0zm14.28 2.53l-5.25 5.25a.75.75 0 01-1.06 0L7 7.06 4.28 9.78a.75.75 0 01-1.06-1.06l3.25-3.25a.75.75 0 011.06 0L10 7.94l4.72-4.72a.75.75 0 111.06 1.06z"/>
            </svg>
            ${count} ${count === 1 ? 'activity' : 'activities'}
        `;
    }
}

function renderActivities() {
    const timeline = document.getElementById('activityTimeline');
    const emptyState = document.getElementById('emptyState');
    
    if (!timeline) return;
    
    // Filter activities
    let filteredActivities = allActivities;
    if (currentFilter !== 'all') {
        filteredActivities = allActivities.filter(activity => activity.type === currentFilter);
    }
    
    // Check if empty
    if (filteredActivities.length === 0) {
        timeline.innerHTML = '';
        if (emptyState) emptyState.style.display = 'flex';
        return;
    }
    
    if (emptyState) emptyState.style.display = 'none';
    
    // Group activities by date
    const groupedActivities = groupByDate(filteredActivities);
    
    // Render
    timeline.innerHTML = '';
    
    Object.keys(groupedActivities).forEach(date => {
        // Add date separator
        const dateSeparator = document.createElement('div');
        dateSeparator.className = 'date-separator';
        dateSeparator.textContent = date;
        timeline.appendChild(dateSeparator);
        
        // Add activities for this date
        groupedActivities[date].forEach(activity => {
            const activityElement = createActivityElement(activity);
            timeline.appendChild(activityElement);
        });
    });
}

function groupByDate(activities) {
    const grouped = {};
    
    activities.forEach(activity => {
        const date = formatDateHeader(activity.timestamp);
        
        if (!grouped[date]) {
            grouped[date] = [];
        }
        
        grouped[date].push(activity);
    });
    
    return grouped;
}

function createActivityElement(activity) {
    const div = document.createElement('div');
    div.className = `activity-item ${activity.type}`;
    
    // Get icon based on activity type
    const icon = getActivityIcon(activity.type);
    
    // Build metadata tags
    let metaTags = '';
    if (activity.repo_name) {
        metaTags += `
            <span class="meta-tag repo">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z"/>
                </svg>
                ${activity.repo_name}
            </span>
        `;
    }
    
    if (activity.file_name) {
        metaTags += `
            <span class="meta-tag file">
                <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                    <path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0113.25 16h-9.5A1.75 1.75 0 012 14.25V1.75z"/>
                </svg>
                ${activity.file_name}
            </span>
        `;
    }
    
    if (activity.language) {
        metaTags += `
            <span class="meta-tag language">
                ${getLanguageIcon(activity.language)}
                ${capitalizeFirst(activity.language)}
            </span>
        `;
    }
    
    div.innerHTML = `
        <div class="activity-header">
            <div class="activity-icon-wrapper">
                ${icon}
            </div>
            <div class="activity-details">
                <div class="activity-title">${activity.title}</div>
                <div class="activity-description">${activity.description}</div>
                ${metaTags ? `<div class="activity-meta">${metaTags}</div>` : ''}
                <div class="activity-time">
                    <svg width="12" height="12" viewBox="0 0 16 16" fill="currentColor">
                        <path d="M8 0a8 8 0 110 16A8 8 0 018 0zM1.5 8a6.5 6.5 0 1013 0 6.5 6.5 0 00-13 0zm7-3.25v2.992l2.028.812a.75.75 0 01-.557 1.392l-2.5-1A.75.75 0 017 8.25v-3.5a.75.75 0 011.5 0z"/>
                    </svg>
                    ${formatTimeAgo(activity.timestamp)}
                </div>
            </div>
        </div>
    `;
    
    // Make clickable if has repo_id
    if (activity.repo_id) {
        div.style.cursor = 'pointer';
        div.addEventListener('click', () => {
            window.location.href = `/repo/${activity.repo_id}`;
        });
    }
    
    return div;
}

function getActivityIcon(type) {
    const icons = {
        'create_repo': `
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8a1 1 0 00-.714 1.7.75.75 0 01-1.072 1.05A2.495 2.495 0 012 11.5v-9zm10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 011-1h8z"/>
            </svg>
        `,
        'create_file': `
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M2 1.75C2 .784 2.784 0 3.75 0h6.586c.464 0 .909.184 1.237.513l2.914 2.914c.329.328.513.773.513 1.237v9.586A1.75 1.75 0 0113.25 16h-9.5A1.75 1.75 0 012 14.25V1.75z"/>
            </svg>
        `,
        'run_code': `
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M4.72 3.22a.75.75 0 011.06 1.06L2.06 8l3.72 3.72a.75.75 0 11-1.06 1.06L.47 8.53a.75.75 0 010-1.06l4.25-4.25zm6.56 0a.75.75 0 10-1.06 1.06L13.94 8l-3.72 3.72a.75.75 0 101.06 1.06l4.25-4.25a.75.75 0 000-1.06l-4.25-4.25z"/>
            </svg>
        `,
        'create_folder': `
            <svg width="20" height="20" viewBox="0 0 16 16" fill="currentColor">
                <path d="M1.75 1A1.75 1.75 0 000 2.75v10.5C0 14.216.784 15 1.75 15h12.5A1.75 1.75 0 0016 13.25v-8.5A1.75 1.75 0 0014.25 3H7.5a.25.25 0 01-.2-.1l-.9-1.2C6.07 1.26 5.55 1 5 1H1.75z"/>
            </svg>
        `
    };
    
    return icons[type] || icons['create_file'];
}

function getLanguageIcon(language) {
    const icons = {
        'python': '🐍',
        'javascript': '📜',
        'java': '☕',
        'cpp': '⚙️',
        'c': '🔧'
    };
    
    return icons[language] || '📄';
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return 'Just now';
    
    const now = new Date();
    const then = new Date(timestamp);
    const seconds = Math.floor((now - then) / 1000);
    
    if (seconds < 60) return 'Just now';
    
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} minute${minutes !== 1 ? 's' : ''} ago`;
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} hour${hours !== 1 ? 's' : ''} ago`;
    
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days} day${days !== 1 ? 's' : ''} ago`;
    
    const weeks = Math.floor(days / 7);
    if (weeks < 4) return `${weeks} week${weeks !== 1 ? 's' : ''} ago`;
    
    const months = Math.floor(days / 30);
    return `${months} month${months !== 1 ? 's' : ''} ago`;
}

function formatDateHeader(timestamp) {
    if (!timestamp) return 'Unknown Date';
    
    const now = new Date();
    const date = new Date(timestamp);
    
    // Check if today
    if (date.toDateString() === now.toDateString()) {
        return 'Today';
    }
    
    // Check if yesterday
    const yesterday = new Date(now);
    yesterday.setDate(yesterday.getDate() - 1);
    if (date.toDateString() === yesterday.toDateString()) {
        return 'Yesterday';
    }
    
    // Check if this week
    const weekAgo = new Date(now);
    weekAgo.setDate(weekAgo.getDate() - 7);
    if (date > weekAgo) {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return days[date.getDay()];
    }
    
    // Otherwise return formatted date
    const options = { year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

function capitalizeFirst(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}