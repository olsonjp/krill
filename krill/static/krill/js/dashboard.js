// Storage usage calculation
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

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', updateStorageUsage); 