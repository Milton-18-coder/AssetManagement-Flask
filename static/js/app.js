// AssetVault Frontend JavaScript Engine

document.addEventListener('DOMContentLoaded', function () {
    // 1. Mobile Sidebar Toggle
    const sidebarToggleBtn = document.getElementById('sidebarToggle');
    const appSidebar = document.querySelector('.app-sidebar');
    
    if (sidebarToggleBtn && appSidebar) {
        sidebarToggleBtn.addEventListener('click', function () {
            appSidebar.classList.toggle('show');
        });
        
        // Close sidebar when clicking outside on mobile
        document.addEventListener('click', function (e) {
            if (window.innerWidth <= 992 && 
                !appSidebar.contains(e.target) && 
                !sidebarToggleBtn.contains(e.target) &&
                appSidebar.classList.contains('show')) {
                appSidebar.classList.remove('show');
            }
        });
    }

    // 2. Global Instant Search
    const searchInput = document.getElementById('globalSearchInput');
    const searchDropdown = document.getElementById('globalSearchResults');
    let searchTimeout = null;

    if (searchInput && searchDropdown) {
        searchInput.addEventListener('input', function () {
            const query = this.value.trim();
            clearTimeout(searchTimeout);

            if (query.length < 2) {
                searchDropdown.style.display = 'none';
                searchDropdown.innerHTML = '';
                return;
            }

            searchTimeout = setTimeout(() => {
                fetch(`/api/search?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        searchDropdown.innerHTML = '';
                        if (data.results && data.results.length > 0) {
                            data.results.forEach(item => {
                                const a = document.createElement('a');
                                a.className = 'search-result-item';
                                a.href = item.url;
                                a.innerHTML = `
                                    <div class="fw-bold text-primary mb-1"><i class="bi bi-box-seam me-1"></i> ${item.title}</div>
                                    <div class="small text-muted">${item.subtitle}</div>
                                `;
                                searchDropdown.appendChild(a);
                            });
                            searchDropdown.style.display = 'block';
                        } else {
                            searchDropdown.innerHTML = `
                                <div class="p-3 text-center text-muted small">
                                    <i class="bi bi-search me-1"></i> No matching assets found for "${query}"
                                </div>
                            `;
                            searchDropdown.style.display = 'block';
                        }
                    })
                    .catch(err => console.error('Search error:', err));
            }, 250);
        });

        // Hide search dropdown on click outside
        document.addEventListener('click', function (e) {
            if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
                searchDropdown.style.display = 'none';
            }
        });
    }
});

// Helper function to trigger generic confirmation modal
function confirmAction(message, formId) {
    if (confirm(message)) {
        document.getElementById(formId).submit();
    }
}
