# Reports app

Reports is where you check that what Krill says is in storage is really there (the **storage audit**), where the items that need attention are listed, and where aliquots checked out with no recorded owner are listed. Open it from **Reports** in the sidebar.

## Storage audit

A spot check of storage. Krill picks stored aliquots at random and gives you a checklist of where to find each one. You go to the freezer, look, and mark each location.

### Run one
1. **Reports > Start Storage Audit** (or **Start Audit** on the dashboard).
2. Give it a name (it defaults to today's date) and a sample size (1 to 100, default 10). Optionally tick **Include empty slot verification** to also check a few slots that should be empty.
3. **Generate Audit Report** opens the checklist.

### The checklist
Each row shows the cell line and aliquot type, the full location (freezer > cane > box > row, column), and the details that help you recognise the tube: passage, date frozen, lab member, disposition, aliquot number and the sample notes.

Mark each row **Correct** (the tube is there; for an empty-slot check, it is empty), **Wrong** (missing or different), and add a note if useful. Every mark is saved as you make it, so you can walk away and carry on later. The row's left edge turns green or red, and the counts at the top (checked, correct, wrong) update.

### Resume, review and clean up
- **Reports** and the **Storage Audits** list (`/reports/audit/list/`) show audits with progress ("12 of 20 checked") and whether each is in progress or complete. The dashboard lists audits still in progress.
- Open any audit to carry on or review it. The list shows everyone's audits (20 per page); **Show only mine** narrows it.
- A row records who checked it, so a review by a lab manager shows up as theirs.
- The trash button deletes an audit permanently, after a confirmation.

### Who can do what
| | View | Mark slots | Delete |
|---|---|---|---|
| Anyone signed in | Any audit | Only audits they started | Only audits they started |
| Lab managers and admins | Any audit | Any audit | Any audit |

Other people see the checklist with the fields disabled.

### How it works
- An audit is a `Report` whose template has the type `storage_audit`. The random sample and each mark live in the report's `result_data` (`audit_slots`, and `empty_audit_slots` if requested), so there is no separate table.
- Each aliquot is one tube, so every occupied slot expects exactly one. The details on each row are read from the aliquot when the page opens, so older audits show current information.
- Saving a mark is `POST /reports/audit/<id>/save/` with the slot's kind, index, result and note.
- If building the sample fails, no report is created.

Code: `reports/views.py` (`generate_audit_report`, `generate_storage_audit_data`, `audit_detail`, `audit_list`, `save_audit_result`, `delete_audit`), templates in `reports/templates/reports/`, tests in `reports/tests.py`.

## Checked out, no owner

**Reports > Checked Out, No Owner** (`/reports/checked-out-no-owner/`) lists aliquots whose disposition is In Use but that have no recorded owner. Since Krill started recording who checks an aliquot out (the Check Out button saves the person and the time), every new checkout has an owner. The ones listed here were set to In Use before that, or by editing the aliquot by hand.

A checked-out aliquot is used and discarded, so most of this list is aliquots that were used long ago and never marked Exhausted. Lab managers and admins can clear them from the page: tick the rows (the box in the header ticks everything on the page), pick a status, and press **Apply**. The status list is every status except Stored and In Use (Exhausted and Disposed), because a checked-out aliquot is never put back in storage. Each change is saved as an "Aliquot Updated" entry in the audit log, and only aliquots that are still In Use with no owner are changed, so a stale page cannot overwrite someone else's edit. Other people see the list without the tick boxes and can still open one aliquot at a time. The page shows the total and 50 aliquots per page, with sample, type, passage, sample date and last-updated date.

A person's own checked-out aliquots are in the Aliquots list with the **Checked out by me** filter (`/samples/list/?type=aliquot&checked_out_by=me`). The owner and time stay on the aliquot after it is exhausted, as a record of who used it.

Code: `checked_out_no_owner` in `reports/views.py` (handles the list and the status change), template `reports/templates/reports/checked_out_no_owner.html`, tests in `reports/test_checked_out_no_owner.py`.

## Needs attention

The pill in the Dashboard header ("All clear", or "N need attention", amber for a warning and red for an alert) opens **Needs Attention** (`/reports/alerts/`). It lists everything that needs action, grouped by what it is about:

- **Low stock:** a consumable at or below its low-stock threshold. It is an alert when it is out of stock and a warning otherwise.
- **Expiring soon:** a consumable that expires within 30 days (warning).

These two only appear when Consumables are turned on in Settings. Items come from your data; nobody types them in. The older manually created alerts are gone (the table was empty in the lab's backup, and the data model is kept).

**Silence.** Lab managers and admins can press **Silence** on an item when the lab does not want to hear about it, for example a consumable it is phasing out. The switch lives on the consumable itself (`alerts_silenced`), so it also leaves the Low Stock and Expiring Soon tiles, their filtered lists and the reorder list. Silenced items stay on the page under **Silenced**, with **Turn back on**. Silencing is saved to the audit log.

**How it is built.** `reports/attention.py` works everything out, and the pill, this page and the Reports page all read from it, so they always agree. Each item has a stable key such as `low_stock:consumable:12`. To add a source, write a function that returns a list of `AttentionItem`, register it with `register_source()`, and (if it can be silenced) register a silencer for its record type. Email notifications, when added, should use the same items and keys to avoid sending the same alert twice.

## Other pieces

- `/reports/list/` lists the signed-in user's own reports, including audits.
- `/reports/storage/dashboard/` shows storage capacity statistics.
- `/reports/dashboard/stats/` returns summary numbers as JSON.
- The `generate_report` endpoint and the report types in `ReportTemplate` (sample inventory, storage capacity, user activity, aliquot tracking) are not offered anywhere in the interface. Only the storage audit can be run from the page today.
