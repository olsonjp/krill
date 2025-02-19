document.addEventListener('DOMContentLoaded', function() {
    const sidebarLinks = document.querySelectorAll('.sidebar a');
    const menuBtn = document.querySelector('#menu-btn');
    
    // Handle sidebar link active states
    sidebarLinks.forEach(link => {
        link.addEventListener('click', function() {
            // Remove active class from all links
            sidebarLinks.forEach(l => l.classList.remove('active'));
            // Add active class to clicked link
            this.classList.add('active');
        });
    });

    // Handle menu button click (if it exists)
    if (menuBtn) {
        menuBtn.addEventListener('click', function() {
            document.querySelector('aside').classList.toggle('collapsed');
        });
    }
}); 