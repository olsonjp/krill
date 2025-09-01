// Settings page functionality
document.addEventListener('DOMContentLoaded', function() {
    // Initialize settings page
    initializeSettings();
    
    // Add event listeners
    setupEventListeners();
});

function initializeSettings() {
    // Load current user preferences
    loadUserPreferences();
    
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
    
    // Other toggle switches
    const toggleSwitches = document.querySelectorAll('.toggle-switch input[type="checkbox"]');
    toggleSwitches.forEach(toggle => {
        if (toggle.id !== 'dark-mode') {
            toggle.addEventListener('change', function() {
                // Mark settings as changed
                markSettingsChanged();
            });
        }
    });
    
    // Select dropdowns
    const selectDropdowns = document.querySelectorAll('.setting-item select');
    selectDropdowns.forEach(select => {
        select.addEventListener('change', function() {
            markSettingsChanged();
        });
    });
    
    // Text inputs
    const textInputs = document.querySelectorAll('.setting-item input[type="text"]');
    textInputs.forEach(input => {
        input.addEventListener('input', function() {
            markSettingsChanged();
        });
    });
}

function loadUserPreferences() {
    // Load current user preferences from the server
    fetch('/preferences/user/', {
        method: 'GET',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'Content-Type': 'application/json',
        },
    })
    .then(response => {
        if (response.ok) {
            return response.json();
        }
        throw new Error('Failed to load preferences');
    })
    .then(data => {
        updateSettingsForm(data);
    })
    .catch(error => {
        console.error('Error loading preferences:', error);
        // Load default preferences
        loadDefaultPreferences();
    });
}

function loadDefaultPreferences() {
    // Set default values for settings
    const defaultSettings = {
        dark_mode: false,
        email_notifications: true,
        language: 'English',
        auto_save_interval: '5 minutes',
        data_retention_period: '90 days',
        default_storage_location: 'Freezer A',
        auto_archive_old_samples: false,
        default_report_format: 'PDF',
        auto_generate_reports: true
    };
    
    updateSettingsForm(defaultSettings);
}

function updateSettingsForm(preferences) {
    // Update dark mode toggle
    const darkModeToggle = document.getElementById('dark-mode');
    if (darkModeToggle) {
        darkModeToggle.checked = preferences.dark_mode || false;
    }
    
    // Update email notifications
    const emailToggle = document.getElementById('email-notifications');
    if (emailToggle) {
        emailToggle.checked = preferences.email_notifications || false;
    }
    
    // Update language
    const languageSelect = document.querySelector('.setting-item select');
    if (languageSelect) {
        languageSelect.value = preferences.language || 'English';
    }
    
    // Update auto-save interval
    const autoSaveSelect = document.querySelectorAll('.setting-item select')[1];
    if (autoSaveSelect) {
        autoSaveSelect.value = preferences.auto_save_interval || '5 minutes';
    }
    
    // Update data retention period
    const retentionSelect = document.querySelectorAll('.setting-item select')[2];
    if (retentionSelect) {
        retentionSelect.value = preferences.data_retention_period || '90 days';
    }
    
    // Update storage location
    const storageSelect = document.querySelectorAll('.setting-item select')[3];
    if (storageSelect) {
        storageSelect.value = preferences.default_storage_location || 'Freezer A';
    }
    
    // Update auto-archive toggle
    const autoArchiveToggle = document.getElementById('auto-archive');
    if (autoArchiveToggle) {
        autoArchiveToggle.checked = preferences.auto_archive_old_samples || false;
    }
    
    // Update report format
    const reportFormatSelect = document.querySelectorAll('.setting-item select')[4];
    if (reportFormatSelect) {
        reportFormatSelect.value = preferences.default_report_format || 'PDF';
    }
    
    // Update auto-reports toggle
    const autoReportsToggle = document.getElementById('auto-reports');
    if (autoReportsToggle) {
        autoReportsToggle.checked = preferences.auto_generate_reports || true;
    }
    
    // Update display name if available
    const displayNameInput = document.querySelector('.setting-item input[type="text"]');
    if (displayNameInput && preferences.display_name) {
        displayNameInput.value = preferences.display_name;
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
            'X-CSRFToken': getCookie('csrftoken'),
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
    // Collect all current settings
    const settings = {
        dark_mode: document.getElementById('dark-mode')?.checked || false,
        email_notifications: document.getElementById('email-notifications')?.checked || false,
        language: document.querySelector('.setting-item select')?.value || 'English',
        auto_save_interval: document.querySelectorAll('.setting-item select')[1]?.value || '5 minutes',
        data_retention_period: document.querySelectorAll('.setting-item select')[2]?.value || '90 days',
        default_storage_location: document.querySelectorAll('.setting-item select')[3]?.value || 'Freezer A',
        auto_archive_old_samples: document.getElementById('auto-archive')?.checked || false,
        default_report_format: document.querySelectorAll('.setting-item select')[4]?.value || 'PDF',
        auto_generate_reports: document.getElementById('auto-reports')?.checked || true,
        display_name: document.querySelector('.setting-item input[type="text"]')?.value || ''
    };
    
    // Save settings to server
    fetch('/preferences/save/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
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
            // Show success message
            alert('Settings saved successfully!');
        } else {
            throw new Error(data.message || 'Failed to save settings');
        }
    })
    .catch(error => {
        console.error('Error saving settings:', error);
        alert('Failed to save settings. Please try again.');
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
