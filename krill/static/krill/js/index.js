const sideMenu = document.querySelector('aside');
const menuBtn = document.getElementById('menu-btn');
const darkMode = document.querySelector('.dark-mode');

menuBtn?.addEventListener('click', () => {
    sideMenu.style.display = 'block';
});

// Initialize dark mode state on page load
function initializeDarkMode() {
    if (darkMode) {
        // Check if body already has dark mode class (set by Django template)
        const isDarkMode = document.body.classList.contains('dark-mode-variables');
        
        // Update the toggle state to match current theme
        const lightIcon = darkMode.querySelector('span:nth-child(1)');
        const darkIcon = darkMode.querySelector('span:nth-child(2)');
        
        if (isDarkMode) {
            lightIcon.classList.remove('active');
            darkIcon.classList.add('active');
        } else {
            lightIcon.classList.add('active');
            darkIcon.classList.remove('active');
        }
    }
}

if (darkMode) {
    // Initialize dark mode state
    initializeDarkMode();
    
    darkMode.addEventListener('click', async () => {
        try {
            const response = await fetch('/preferences/theme/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json',
                },
            });
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }

            const data = await response.json();
            // Update body class based on the server response
            if (data.dark_mode) {
                document.body.classList.add('dark-mode-variables');
            } else {
                document.body.classList.remove('dark-mode-variables');
            }
            // Toggle the active class on the icons
            const lightIcon = darkMode.querySelector('span:nth-child(1)');
            const darkIcon = darkMode.querySelector('span:nth-child(2)');
            if (data.dark_mode) {
                lightIcon.classList.remove('active');
                darkIcon.classList.add('active');
            } else {
                lightIcon.classList.add('active');
                darkIcon.classList.remove('active');
            }
        } catch (error) {
            console.error('Error:', error);
        }
    });
}

// Helper function to get CSRF token
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
} 