// Dashboard statistics update
async function updateDashboardStats() {
    try {
        const response = await fetch('/dashboard/stats/');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        // Update Active Samples
        const sampleCard = Array.from(document.querySelectorAll('.stat-card')).find(card => 
            card.querySelector('.material-icons-round').textContent.trim() === 'science'
        );
        if (sampleCard) {
            const sampleElement = sampleCard.querySelector('.stat-info p');
            if (sampleElement) {
                sampleElement.textContent = data.active_samples || 0;
            }
        }
        // Update Storage Usage
        const storageCard = Array.from(document.querySelectorAll('.stat-card')).find(card => 
            card.querySelector('.material-icons-round').textContent.trim() === 'inventory_2'
        );
        if (storageCard) {
            const percentageElement = storageCard.querySelector('.stat-info p');
            if (percentageElement) {
                percentageElement.textContent = `${data.storage_usage || 0}%`;
            }
        }
        // Update Reports
        const reportCard = Array.from(document.querySelectorAll('.stat-card')).find(card => 
            card.querySelector('.material-icons-round').textContent.trim() === 'description'
        );
        if (reportCard) {
            const reportElement = reportCard.querySelector('.stat-info p');
            if (reportElement) {
                reportElement.textContent = `${data.recent_reports || 0} Recent`;
            }
        }
        // Update Alerts
        const alertCard = Array.from(document.querySelectorAll('.stat-card')).find(card => 
            card.querySelector('.material-icons-round').textContent.trim() === 'warning'
        );
        if (alertCard) {
            const alertElement = alertCard.querySelector('.stat-info p');
            if (alertElement) {
                alertElement.textContent = `${data.alerts || 0} New`;
            }
        }
    } catch (error) {
        console.error('Error fetching dashboard stats:', error);
    }
}

// Storage usage calculation (keeping for backward compatibility)
async function updateStorageUsage() {
    try {
        const response = await fetch('/storage/capacity/');
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        // Calculate percentage used
        const percentageUsed = Math.round((data.used_slots / data.total_slots) * 100) || 0;
        // Find the storage usage stat card
        const storageCards = document.querySelectorAll('.stat-card');
        const storageCard = Array.from(storageCards).find(card => 
            card.querySelector('.material-icons-round').textContent.trim() === 'inventory_2'
        );
        if (storageCard) {
            const percentageElement = storageCard.querySelector('.stat-info p');
            if (percentageElement) {
                percentageElement.textContent = `${percentageUsed}%`;
            }
        }
    } catch (error) {
        console.error('Error fetching storage capacity:', error);
    }
}

// Call the functions when the page loads
document.addEventListener('DOMContentLoaded', function() {
    updateDashboardStats();
    // Keep the storage usage update for backward compatibility
    // updateStorageUsage();
}); 