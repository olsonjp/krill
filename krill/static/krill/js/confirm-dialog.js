// Two-click confirmation in an in-page dialog instead of the browser's confirm() popup.
//
// Add data-confirm="Message" to a <form> (and optionally data-confirm-label="Button text").
// Submitting the form then shows the dialog; the form is only sent when the person confirms.
(function () {
    var dialog = null;
    var pendingForm = null;

    function build() {
        dialog = document.createElement('dialog');
        dialog.className = 'confirm-dialog';
        dialog.setAttribute('aria-labelledby', 'confirmDialogMessage');
        dialog.innerHTML =
            '<p id="confirmDialogMessage" class="confirm-dialog-message"></p>' +
            '<div class="confirm-dialog-actions">' +
            '<button type="button" class="btn btn-sm btn-plain" data-confirm-cancel>Cancel</button>' +
            '<button type="button" class="btn btn-sm btn-primary" data-confirm-ok autofocus></button>' +
            '</div>';
        document.body.appendChild(dialog);

        dialog.querySelector('[data-confirm-cancel]').addEventListener('click', function () {
            pendingForm = null;
            dialog.close();
        });
        dialog.querySelector('[data-confirm-ok]').addEventListener('click', function () {
            var form = pendingForm;
            pendingForm = null;
            dialog.close();
            if (form) {
                form.removeAttribute('data-confirm-pending');
                form.submit();  // submit() does not fire the submit event, so this does not loop
            }
        });
        // Esc, or a click on the dimmed backdrop, cancels
        dialog.addEventListener('cancel', function () { pendingForm = null; });
        dialog.addEventListener('click', function (e) {
            if (e.target === dialog) { pendingForm = null; dialog.close(); }
        });
    }

    document.addEventListener('submit', function (event) {
        var form = event.target;
        if (!form || !form.getAttribute || !form.getAttribute('data-confirm')) return;
        event.preventDefault();
        if (!dialog) build();
        pendingForm = form;
        dialog.querySelector('.confirm-dialog-message').textContent = form.getAttribute('data-confirm');
        dialog.querySelector('[data-confirm-ok]').textContent = form.getAttribute('data-confirm-label') || 'Confirm';
        dialog.showModal();
    });
})();
