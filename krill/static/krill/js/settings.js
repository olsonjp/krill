// Settings page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize settings page
    initializeSettings();

    // Add event listeners
    setupEventListeners();
});

function initializeSettings() {
    // Set initial dark mode toggle state - do this after a short delay to ensure DOM is ready
    setTimeout(() => {
        updateDarkModeToggle();
    }, 100);
}

function setupEventListeners() {
    // Dark mode toggle
    const darkModeToggle = document.getElementById('dark-mode');
    if (darkModeToggle) {
        darkModeToggle.addEventListener('change', function() {
            handleDarkModeToggle(this.checked);
        });
    }

    // Save settings button
    const saveButton = document.querySelector('.save-settings');
    if (saveButton) {
        saveButton.addEventListener('click', saveAllSettings);
    }

    // Display name input
    const displayNameInput = document.querySelector('.setting-item input[type="text"]');
    if (displayNameInput) {
        displayNameInput.addEventListener('input', function() {
            markSettingsChanged();
        });
    }
}

function updateDarkModeToggle() {
    // Check if body has dark mode class and update toggle accordingly
    const isDarkMode = document.body.classList.contains('dark-mode-variables');
    const darkModeToggle = document.getElementById('dark-mode');
    if (darkModeToggle) {
        darkModeToggle.checked = isDarkMode;
    }
}

function handleDarkModeToggle(isDarkMode) {
    // Call the existing theme toggle endpoint
    fetch('/preferences/theme/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json',
        },
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        }
        throw new Error('Failed to toggle theme');
    })
    .then(data => {
        // Update body class
        if (data.dark_mode) {
            document.body.classList.add('dark-mode-variables');
        } else {
            document.body.classList.remove('dark-mode-variables');
        }

        // Update header toggle state
        const headerDarkMode = document.querySelector('.header .dark-mode');
        if (headerDarkMode) {
            const lightIcon = headerDarkMode.querySelector('span:nth-child(1)');
            const darkIcon = headerDarkMode.querySelector('span:nth-child(2)');

            if (data.dark_mode) {
                lightIcon.classList.remove('active');
                darkIcon.classList.add('active');
            } else {
                lightIcon.classList.add('active');
                darkIcon.classList.remove('active');
            }
        }

        markSettingsChanged();
    })
    .catch(error => {
        console.error('Error toggling theme:', error);
        // Revert toggle state on error
        const darkModeToggle = document.getElementById('dark-mode');
        if (darkModeToggle) {
            darkModeToggle.checked = !isDarkMode;
        }
    });
}

function markSettingsChanged() {
    // Simple function to mark that settings have changed
    // No need to modify the save button since we're using original styling
}

function saveAllSettings() {
    // Collect current settings (only the ones that actually exist)
    const settings = {
        dark_mode: document.getElementById('dark-mode')?.checked || false,
        display_name: document.querySelector('.setting-item input[type="text"]')?.value || ''
    };

    // Show loading state on save button
    const saveButton = document.querySelector('.save-settings');
    const originalText = saveButton.textContent;
    saveButton.textContent = 'Saving...';
    saveButton.disabled = true;

    // Save settings to server
    fetch('/preferences/save/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value,
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(settings)
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        }
        throw new Error('Failed to save settings');
    })
    .then(data => {
        if (data.success) {
            // Show subtle success message
            showSuccessMessage('Settings saved successfully!');

            // Refresh the page after a short delay to reflect new state
            setTimeout(() => {
                window.location.reload();
            }, 1000);
        } else {
            throw new Error(data.message || 'Failed to save settings');
        }
    })
    .catch(error => {
        console.error('Error saving settings:', error);
        showErrorMessage('Failed to save settings. Please try again.');

        // Reset save button
        saveButton.textContent = originalText;
        saveButton.disabled = false;
    });
}

function showSuccessMessage(message) {
    // Remove any existing messages
    removeExistingMessages();

    // Create success message element
    const successDiv = document.createElement('div');
    successDiv.className = 'settings-message success';
    successDiv.innerHTML = `
        <span class="material-icons-round">check_circle</span>
        <span>${message}</span>
    `;

    // Insert before the save button
    const saveButton = document.querySelector('.save-settings');
    saveButton.parentNode.insertBefore(successDiv, saveButton);

    // Auto-remove after 3 seconds
    setTimeout(() => {
        if (successDiv.parentNode) {
            successDiv.remove();
        }
    }, 3000);
}

function showErrorMessage(message) {
    // Remove any existing messages
    removeExistingMessages();

    // Create error message element
    const errorDiv = document.createElement('div');
    errorDiv.className = 'settings-message error';
    errorDiv.innerHTML = `
        <span class="material-icons-round">error</span>
        <span>${message}</span>
    `;

    // Insert before the save button
    const saveButton = document.querySelector('.save-settings');
    saveButton.parentNode.insertBefore(errorDiv, saveButton);

    // Auto-remove after 5 seconds
    setTimeout(() => {
        if (errorDiv.parentNode) {
            errorDiv.remove();
        }
    }, 5000);
}

function removeExistingMessages() {
    // Remove any existing message elements
    const existingMessages = document.querySelectorAll('.settings-message');
    existingMessages.forEach(msg => msg.remove());
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
