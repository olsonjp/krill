// Dashboard statistics update
async function updateDashboardStats() {
    // Show loading state
    showLoadingState();
    
    try {
        const response = await fetch('/dashboard/stats/');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
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
                sampleElement.classList.remove('loading');
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
                percentageElement.classList.remove('loading');
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
                reportElement.classList.remove('loading');
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
                alertElement.classList.remove('loading');
            }
        }
        
        // Hide loading state
        hideLoadingState();
        
    } catch (error) {
        console.error('Error fetching dashboard stats:', error);
        showErrorState();
    }
}

// Show loading state
function showLoadingState() {
    const statCards = document.querySelectorAll('.stat-card .stat-info p');
    statCards.forEach(element => {
        element.classList.add('loading');
        element.textContent = 'Loading...';
    });
}

// Hide loading state
function hideLoadingState() {
    const loadingElements = document.querySelectorAll('.loading');
    loadingElements.forEach(element => {
        element.classList.remove('loading');
    });
}

// Show error state
function showErrorState() {
    const statCards = document.querySelectorAll('.stat-card .stat-info p');
    statCards.forEach(element => {
        element.classList.add('error');
        element.textContent = 'Error';
    });
    
    // Show error notification
    showNotification('Failed to load dashboard statistics. Please refresh the page.', 'error');
}

// Show notification
function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 12px 20px;
        border-radius: 4px;
        color: white;
        font-weight: 500;
        z-index: 1000;
        opacity: 0;
        transform: translateX(100%);
        transition: all 0.3s ease;
    `;
    
    // Set background color based on type
    if (type === 'error') {
        notification.style.backgroundColor = '#dc3545';
    } else if (type === 'success') {
        notification.style.backgroundColor = '#28a745';
    } else {
        notification.style.backgroundColor = '#007bff';
    }
    
    // Add to page
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 100);
    
    // Remove after 5 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 5000);
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