// Type-to-filter for <select> fields.
//
// A <select data-combobox> is replaced by a text box with a list under it. The original <select>
// stays in the page (visually hidden) and holds the value, so Django's form fields, validation,
// prefilled values and form submission are unchanged. Lists shorter than MIN_OPTIONS stay plain
// selects, because a short native list is easier to use.
//
//   Local lists    The options already in the <select> are filtered as you type. Every word
//                  typed must appear in an option ("hela p8" finds "HeLa #12 · Cells · p8").
//   Remote lists   A <select data-search-url="..."> holds only its current choice. What is typed is
//                  sent to that address (?q=...), which answers {results: [{id, label}], more: bool}.
//
// Keyboard: Down/Up move through the list, Enter chooses, Esc closes. It follows the ARIA
// combobox pattern (role=combobox on the text box, role=listbox and role=option for the list).
(function () {
    'use strict';

    var MIN_OPTIONS = 8;     // fewer than this and the native select is left alone
    var LOCAL_LIMIT = 100;   // most matches shown for a local list
    var DEBOUNCE_MS = 200;
    var counter = 0;

    // If setting a field up fails part way, put the plain <select> back so the field never disappears
    function undo(select) {
        var wrapper = select.closest('.combobox');
        if (wrapper && wrapper.parentNode) {
            wrapper.parentNode.insertBefore(select, wrapper);
            wrapper.parentNode.removeChild(wrapper);
        }
        select.classList.remove('combobox-native');
        select.removeAttribute('aria-hidden');
        select.removeAttribute('tabindex');
        delete select.dataset.comboboxReady;
        if (select.id) {
            Array.prototype.forEach.call(
                document.querySelectorAll('label[data-combobox-for="' + select.id + '"]'),
                function (label) { label.setAttribute('for', select.id); }
            );
        }
    }

    function init(select) {
        try {
            enhance(select);
        } catch (error) {
            undo(select);
            if (window.console) { console.error('Type-to-filter could not start for', select.name, error); }
        }
    }

    function enhance(select) {
        if (select.dataset.comboboxReady) { return; }
        var searchUrl = select.getAttribute('data-search-url');
        if (!searchUrl && select.options.length - 1 < MIN_OPTIONS) { return; }
        select.dataset.comboboxReady = '1';
        var originalClasses = select.className;   // the text box takes the select's look (for example form-control)

        var id = 'combobox-' + (++counter);
        var wrapper = document.createElement('div');
        wrapper.className = 'combobox';
        select.parentNode.insertBefore(wrapper, select);
        wrapper.appendChild(select);
        select.classList.add('combobox-native');
        select.tabIndex = -1;
        select.setAttribute('aria-hidden', 'true');

        var input = document.createElement('input');
        input.type = 'text';
        input.id = id + '-input';
        input.className = ('combobox-input ' + originalClasses).trim();
        input.autocomplete = 'off';
        input.spellcheck = false;
        input.disabled = select.disabled;
        input.setAttribute('role', 'combobox');
        input.setAttribute('aria-autocomplete', 'list');
        input.setAttribute('aria-haspopup', 'listbox');
        input.setAttribute('aria-expanded', 'false');
        input.setAttribute('aria-controls', id + '-list');
        input.placeholder = searchUrl ? 'Type to search' : 'Type to filter';
        if (select.getAttribute('aria-describedby')) {
            input.setAttribute('aria-describedby', select.getAttribute('aria-describedby'));
        }

        var clear = document.createElement('button');
        clear.type = 'button';
        clear.className = 'combobox-clear';
        clear.setAttribute('aria-label', 'Clear selection');
        clear.textContent = '×';

        var list = document.createElement('ul');
        list.id = id + '-list';
        list.className = 'combobox-list';
        list.setAttribute('role', 'listbox');
        list.hidden = true;

        var status = document.createElement('div');
        status.className = 'combobox-status';
        status.setAttribute('role', 'status');
        status.setAttribute('aria-live', 'polite');

        wrapper.appendChild(input);
        wrapper.appendChild(clear);
        wrapper.appendChild(list);
        wrapper.appendChild(status);

        // The label points at the hidden select; send clicks to the text box instead
        var label = select.id ? document.querySelector('label[for="' + select.id + '"]') : null;
        if (label) {
            label.setAttribute('data-combobox-for', select.id);
            label.setAttribute('for', input.id);
            list.setAttribute('aria-label', label.textContent.replace(/[:*\s]+$/, ''));
        }

        var items = [];        // what the list is showing: [{value, label}]
        var active = -1;       // index of the highlighted item
        var timer = null;
        var request = null;

        function selectedLabel() {
            var option = select.options[select.selectedIndex];
            return option && option.value !== '' ? option.text : '';
        }

        function syncFromSelect() {
            input.value = selectedLabel();
            clear.hidden = select.value === '' || select.disabled;
        }

        function isOpen() { return !list.hidden; }

        function setActive(index) {
            var nodes = list.querySelectorAll('[role="option"]');
            if (active >= 0 && nodes[active]) {
                nodes[active].removeAttribute('aria-selected');
                nodes[active].classList.remove('is-active');
            }
            active = index;
            if (active >= 0 && nodes[active]) {
                nodes[active].setAttribute('aria-selected', 'true');
                nodes[active].classList.add('is-active');
                input.setAttribute('aria-activedescendant', nodes[active].id);
                nodes[active].scrollIntoView({ block: 'nearest' });
            } else {
                input.removeAttribute('aria-activedescendant');
            }
        }

        function open() {
            list.hidden = false;
            input.setAttribute('aria-expanded', 'true');
        }

        function close() {
            list.hidden = true;
            input.setAttribute('aria-expanded', 'false');
            input.removeAttribute('aria-activedescendant');
            active = -1;
            if (request) { request.abort(); request = null; }
            clearTimeout(timer);
        }

        function render(newItems, message) {
            items = newItems;
            list.textContent = '';
            newItems.forEach(function (item, index) {
                var li = document.createElement('li');
                li.id = id + '-option-' + index;
                li.className = 'combobox-option';
                li.setAttribute('role', 'option');
                li.dataset.index = index;
                li.textContent = item.label;
                if (item.value === select.value) { li.classList.add('is-current'); }
                list.appendChild(li);
            });
            if (message) {
                var note = document.createElement('li');
                note.className = 'combobox-message';
                note.setAttribute('role', 'presentation');
                note.textContent = message;
                list.appendChild(note);
            }
            active = -1;
            input.removeAttribute('aria-activedescendant');
            status.textContent = newItems.length
                ? newItems.length + (newItems.length === 1 ? ' result' : ' results') + ' available'
                : (message || '');
            open();
        }

        function localOptions() {
            return Array.prototype.slice.call(select.options)
                .filter(function (o) { return o.value !== ''; })
                .map(function (o) { return { value: o.value, label: o.text }; });
        }

        function showLocal(text) {
            var words = text.toLowerCase().split(/\s+/).filter(Boolean);
            var matches = localOptions().filter(function (item) {
                var haystack = item.label.toLowerCase();
                return words.every(function (w) { return haystack.indexOf(w) !== -1; });
            });
            var shown = matches.slice(0, LOCAL_LIMIT);
            var message = null;
            if (!matches.length) { message = 'No matches'; }
            else if (matches.length > shown.length) { message = 'Keep typing to narrow the ' + matches.length + ' matches'; }
            render(shown, message);
        }

        function showRemote(text) {
            clearTimeout(timer);
            if (request) { request.abort(); request = null; }
            if (!text.trim()) {
                render([], 'Type a sample name, passage or aliquot number');
                return;
            }
            timer = setTimeout(function () {
                request = typeof AbortController === 'function' ? new AbortController() : null;
                fetch(searchUrl + (searchUrl.indexOf('?') === -1 ? '?' : '&') + 'q=' + encodeURIComponent(text), {
                    credentials: 'same-origin',
                    headers: { 'X-Requested-With': 'XMLHttpRequest' },
                    signal: request ? request.signal : undefined
                }).then(function (response) {
                    if (!response.ok) { throw new Error('bad status'); }
                    return response.json();
                }).then(function (data) {
                    var found = data.results.map(function (r) { return { value: String(r.id), label: r.label }; });
                    render(found, !found.length ? 'No matches' : (data.more ? 'Keep typing to narrow the results' : null));
                }).catch(function (error) {
                    if (error && error.name === 'AbortError') { return; }
                    render([], 'Search is unavailable. Try again.');
                });
            }, DEBOUNCE_MS);
        }

        function search(text) {
            if (searchUrl) { showRemote(text); } else { showLocal(text); }
        }

        function choose(item) {
            if (searchUrl) {
                // The select only holds the current choice, so replace it
                while (select.options.length > 1) { select.remove(1); }
                select.add(new Option(item.label, item.value, true, true));
            }
            select.value = item.value;
            close();
            syncFromSelect();
            select.dispatchEvent(new Event('change', { bubbles: true }));
        }

        function clearChoice() {
            if (searchUrl) { while (select.options.length > 1) { select.remove(1); } }
            select.value = '';
            syncFromSelect();
            select.dispatchEvent(new Event('change', { bubbles: true }));
            input.focus();
        }

        input.addEventListener('focus', function () {
            input.select();
            // Browsing: show everything for a local list; a remote list waits for typing
            if (searchUrl) { render([], 'Type a sample name, passage or aliquot number'); } else { showLocal(''); }
        });

        input.addEventListener('input', function () { search(input.value); });

        input.addEventListener('keydown', function (event) {
            var count = items.length;
            if (event.key === 'ArrowDown') {
                event.preventDefault();
                if (!isOpen()) { search(input.value === selectedLabel() ? '' : input.value); return; }
                if (count) { setActive((active + 1) % count); }
            } else if (event.key === 'ArrowUp') {
                event.preventDefault();
                if (isOpen() && count) { setActive(active <= 0 ? count - 1 : active - 1); }
            } else if (event.key === 'Enter') {
                if (isOpen() && active >= 0 && items[active]) {
                    event.preventDefault();   // choosing must not also submit the form
                    choose(items[active]);
                } else if (isOpen() && count === 1) {
                    event.preventDefault();
                    choose(items[0]);
                }
            } else if (event.key === 'Escape') {
                if (isOpen()) {
                    event.preventDefault();
                    event.stopPropagation();
                    close();
                    syncFromSelect();
                }
            }
        });

        // Keep focus in the text box while the list is clicked, so blur does not close it first
        list.addEventListener('mousedown', function (event) { event.preventDefault(); });
        list.addEventListener('click', function (event) {
            var node = event.target.closest('[role="option"]');
            if (node && items[node.dataset.index]) { choose(items[node.dataset.index]); }
        });
        list.addEventListener('mousemove', function (event) {
            var node = event.target.closest('[role="option"]');
            if (node && Number(node.dataset.index) !== active) { setActive(Number(node.dataset.index)); }
        });
        clear.addEventListener('click', clearChoice);

        input.addEventListener('blur', function () {
            close();
            syncFromSelect();   // text that was typed but not chosen is dropped
        });

        // Another script changed the select (for example create.html clearing the box field)
        select.addEventListener('change', syncFromSelect);
        if (select.form) {
            select.form.addEventListener('reset', function () { setTimeout(syncFromSelect, 0); });
        }

        syncFromSelect();
    }

    function initAll(root) {
        Array.prototype.forEach.call((root || document).querySelectorAll('select[data-combobox]'), init);
    }

    window.krillCombobox = { init: init, initAll: initAll };
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function () { initAll(); });
    } else {
        initAll();
    }
})();
