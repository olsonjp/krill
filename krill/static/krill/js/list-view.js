(function () {
    var STORAGE_KEY = 'krill_view_mode';
    var GRID_PAGE_SIZE = '20';

    function getMode() {
        return sessionStorage.getItem(STORAGE_KEY) || 'table';
    }

    function applyMode(mode) {
        var tableEl = document.querySelector('.view-table');
        var gridEl = document.querySelector('.view-grid');
        var tableBtnEl = document.querySelector('.toggle-table');
        var gridBtnEl = document.querySelector('.toggle-grid');
        if (!tableEl || !gridEl) return;
        tableEl.hidden = (mode !== 'table');
        gridEl.hidden = (mode !== 'grid');
        if (tableBtnEl) tableBtnEl.classList.toggle('active', mode === 'table');
        if (gridBtnEl) gridBtnEl.classList.toggle('active', mode === 'grid');
    }

    window.krillToggleView = function (next) {
        if (next === 'table') {
            sessionStorage.removeItem(STORAGE_KEY);
        } else {
            sessionStorage.setItem(STORAGE_KEY, next);
        }
        var url = new URL(window.location.href);
        if (next === 'grid') {
            url.searchParams.set('page_size', GRID_PAGE_SIZE);
        } else {
            url.searchParams.delete('page_size');
        }
        url.searchParams.delete('page');  // reset to page 1 on view switch
        window.location.href = url.toString();
    };

    function makeRowsClickable() {
        document.querySelectorAll('.items-table tbody tr').forEach(function (row) {
            row.addEventListener('click', function (e) {
                if (e.target.closest('a, button')) return;
                var link = row.querySelector('a');
                if (link) link.click();
            });
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        applyMode(getMode());
        makeRowsClickable();
    });
}());
