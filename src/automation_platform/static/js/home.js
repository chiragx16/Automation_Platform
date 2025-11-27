// static/js/home.js
const fmt = (n)=> new Intl.NumberFormat().format(n);

/**
 * Helper function to format the completed_at timestamp into a readable string.
 * @param {string} timestamp - The ISO-like timestamp (e.g., "2025-11-24 18:15:00").
 * @returns {string} Formatted date/time string.
 */
function formatRunTime(timestamp) {
    // The input format is 'YYYY-MM-DD HH:MM:SS', which is not standard ISO,
    // so we replace the space with 'T' for robust Date parsing.
    const date = new Date(timestamp.replace(' ', 'T'));
    
    // Check if the date is valid
    if (isNaN(date)) {
        return timestamp; 
    }

    const timeOptions = { hour: '2-digit', minute: '2-digit', second: '2-digit' };
    const dateOptions = { month: 'short', day: 'numeric' };

    const formattedTime = date.toLocaleTimeString('en-US', timeOptions);
    const formattedDate = date.toLocaleDateString('en-US', dateOptions);

    return `${formattedDate} at ${formattedTime}`;
}


/**
 * Helper function to get Tailwind CSS classes for the run status.
 * @param {string} status - The status string (e.g., 'SUCCESS', 'FAILURE').
 * @returns {object} An object containing text and badge classes.
 */
function getStatusClasses(status) {
    switch (status.toUpperCase()) {
        case 'SUCCESS':
            return { 
                textClass: 'text-emerald-600', 
                bgClass: 'bg-emerald-100 text-emerald-800' 
            };
        case 'FAILED':
            return { 
                textClass: 'text-red-600', 
                bgClass: 'bg-red-100 text-red-800' 
            };
        case 'RUNNING':
            return { 
                textClass: 'text-brand-600', 
                bgClass: 'bg-brand-100 text-brand-800' 
            };
        case 'TIMEOUT':
            return { 
                textClass: 'text-brand-600', 
                bgClass: 'bg-yellow-100 text-yellow-800' 
            };
        default:
            return { 
                textClass: 'text-gray-600', 
                bgClass: 'bg-gray-100 text-gray-800' 
            };
    }
}


async function loadHome() {
    // 1. Load Stats/KPIs (Existing logic)
    try {
        const statsRes = await fetch('/api/home/stats');
        const stats = await statsRes.json();

        const total = stats.total_bots;
        const activeCount = stats.active_bots;
        const totalUsers = stats.total_users;

        // KPI Updates
        document.getElementById('kpi-total').textContent = fmt(total);
        document.getElementById('kpi-active').textContent = fmt(activeCount);
        document.getElementById('kpi-users').textContent = fmt(totalUsers);

        // Bars
        document.getElementById('kpi-total-bar').style.width = '100%';
        document.getElementById('kpi-active-bar').style.width = Math.min(100, (activeCount / (total || 1)) * 100) + '%';

    } catch (error) {
        console.error("Failed to load dashboard stats:", error);
    }
    
    // --- 2. Load Recent Runs (NEW LOGIC) ---
    try {
        const recentRes = await fetch('/api/home/latest_executions');
        if (!recentRes.ok) {
            throw new Error(`Failed to fetch recent runs. Status: ${recentRes.status}`);
        }
        
        const recentRuns = await recentRes.json();
        const recentList = document.getElementById('recent-list');
        
        recentList.innerHTML = ''; // Clear existing content

        if (recentRuns.length === 0) {
            recentList.innerHTML = '<p class="text-gray-500 text-sm py-4 text-center">No recent executions found.</p>';
        } else {
            recentRuns.slice(0, 5).forEach(run => {
                const { textClass, bgClass } = getStatusClasses(run.status);
                const formattedTime = formatRunTime(run.completed_at);
                
                const listItem = document.createElement('div');
                listItem.className = 'flex items-center justify-between p-3 rounded-lg hover:bg-gray-50 transition border border-gray-100';
                
                listItem.innerHTML = `
                    <div class="flex flex-col">
                        <span class="font-medium text-gray-800">${run.bot_name}</span>
                        <span class="text-xs text-gray-500 mt-0.5">Completed ${formattedTime}</span>
                    </div>
                    <span class="px-2 py-0.5 rounded-full text-xs font-semibold uppercase ${bgClass}">
                        ${run.status}
                    </span>
                `;
                
                recentList.appendChild(listItem);
            });
        }

    } catch (error) {
        console.error("Failed to load recent executions:", error);
        document.getElementById('recent-list').innerHTML = `<p class="text-red-600 text-sm py-4 text-center">Error loading run data.</p>`;
    }
}

document.addEventListener('DOMContentLoaded', loadHome);