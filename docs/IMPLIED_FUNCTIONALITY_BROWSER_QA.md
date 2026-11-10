# Implied Functionality — Browser QA Findings

**Date:** 2026-02-01  
**Method:** Browser MCP testing against running server (http://localhost:8000, credentials admin/admin).  
**Scope:** Areas that are broken, misleading, or missing relative to what the UI implies.

---

## 1. Summary of browser testing performed

- **Login** — Success; redirect to home.
- **Dashboard (home)** — Stats, Recent Activity (empty), Quick Actions, sidebar nav.
- **Samples** — List, detail (sample 23), Create New Sample form (loads); View buttons work.
- **Storage** — Landing page, Sites/Devices/Shelves/Boxes sub-nav, Freezer cards, Quick Actions.
- **Reports** — Dashboard, Report list, Generate Report modal (template/name/format); View All → report list / alert list.
- **Admin** — Expand/collapse; User Management, Create User, Audit Log, Permissions, Data Import, System Admin (all reachable).
- **Data Import** — Page loads; Upload CSV, Preview Import, expected format text present.
- **Settings** — Not exercised in initial pass (tested in follow-up below).
- **Direct URL test** — `/samples/23/` returns **404** (used to confirm wrong Recent Activity URL).

---

## 1b. Follow-up testing (items previously “not tested”)

**Date:** 2026-02-01 (second pass). Same server and credentials.

| Area | Result | Notes |
|------|--------|--------|
| **Create Sample form submission** | **Pass** | Filled Name, Source, Notes, Access level; submitted; redirected to sample list; count increased 67 → 68. New sample `QA_TEST_SAMPLE_001` visible. |
| **Create Aliquot form submission** | **Pass** | Selected Sample (QA_TEST_SAMPLE_001), Aliquot type (Cells), Quantity 1; submitted; redirected to aliquot list; count increased 871 → 872. |
| **Data Import file upload and preview** | **Partial** | Preview Import button is clickable. File upload could not be exercised via browser MCP (no support for setting file input). Actual CSV upload/preview should be tested manually. |
| **Settings (Display Name, Change Password, Dark Mode)** | **Pass** | Display Name: changed to “Admin User”, Save → “Settings saved successfully!”; sidebar updated to “Hey, Admin User”. Change Password: link opens `/users/change-password/` with Current/New/Confirm fields and Cancel. Dark Mode: checkbox toggles; Save persists. Display Name reverted to “admin” after test. |
| **Storage “View Contents” on a freezer** | **Partial** | “View Contents” on FREEZER_FNO navigates to `/storage/devices/?search=FREEZER_FNO`. Page shows “Sites” list (1 site, Default Site) rather than device-specific contents; may be intended (filtered devices list) or a view/URL mismatch. |
| **Storage box assignment** | **Pass** | Create Aliquot with “Assign to box” checked, Box 1_A, Start row 1, Start column 1; submitted; aliquot created and assigned (position 1,1 was occupied so system used next available, 1,10). Count 872 → 873. |
| **Change Password submission** | **Pass** | Changed password admin → admin2, redirected to Settings; then admin2 → admin and reverted. Both submissions succeeded. |
| **Sample detail Edit button** | **Pass** | Edit toggles inline form (Name, Source, Notes, Access level, Save, Cancel). Cancel returns to detail view. Form does not include Experiment field (consistent with 3.1). |

---

## 2. Non-functional / broken behavior

### 2.1 Recent Activity links (Dashboard) — BROKEN when activity exists

- **Where:** [krill/templates/krill/home.html](krill/templates/krill/home.html) — `navigateToActivity()` (lines 215–236).
- **What:** For sample actions, JS navigates to `/samples/${targetId}/`. For aliquot actions, to `/samples/aliquots/${targetId}/`.
- **Actual routes** (from [krill/sample/urls.py](krill/sample/urls.py)): Sample detail: `/samples/detail/<type>/<pk>/` (e.g. `detail/sample/23/`). Aliquot detail: same pattern `detail/aliquot/<pk>/`. Tube detail: `/samples/tube/<pk>/`.
- **Observed:** Visiting `/samples/23/` returns **404**. There is no route `samples/aliquots/<id>/`.
- **Implied functionality to implement:**
  - For **sample** actions: use `/samples/detail/sample/${targetId}/`.
  - For **aliquot** actions: use `/samples/detail/aliquot/${targetId}/` (audit log `target_id` is the aliquot pk from [get_recent_activity()](krill/krill/views/home.py) in home.py).
  - Update `navigateToActivity()` (and optionally use Django-rendered URLs from the template) so Recent Activity items open the correct detail pages instead of 404.

---

## 3. Missing or inconsistent functionality implied by the UI

### 3.1 Create Sample form missing Experiment field

- **Where:** [krill/sample/forms.py](krill/sample/forms.py) — `SampleForm` has `fields = ['name', 'source', 'notes', 'access_level']`. Sample model in [krill/sample/models/sample.py](krill/sample/models/sample.py) has `experiment = models.TextField(blank=True, null=True)`.
- **UI:** Sample **detail** page shows “Experiment: EXP_W21B”. Create Sample form only shows Name, Source, Notes, Access level.
- **Implied functionality:** Add `experiment` to `SampleForm` (create and edit) so users can set or change experiment from the UI; keep it optional to match the model.

### 3.2 Data Import — disposition and terminology (documentation / UX)

- **Reference:** Existing [docs/UX_QA_FINDINGS_BREAST_CANCER_RESEARCH.md](docs/UX_QA_FINDINGS_BREAST_CANCER_RESEARCH.md) (issues 3 and 4).
- **Implied functionality:** Align Data Import disposition values with the model (e.g. document and accept “Stored”, “In Use”, “Exhausted”, “Disposed”) and clarify in UI/docs that “Cell Line” in CSV maps to “Sample” in the app (so “Create New Sample” is the right action for cell lines).

---

## 4. Optional / minor

- **Admin sidebar parent link:** Admin item uses `href="#"` and only expands the submenu. Consider a proper URL or aria attributes for the parent if you want a dedicated “Admin” landing page or better accessibility.
- **Reports “View All” buttons:** Confirmed they navigate to report list and alert list; no change needed for those.

---

## 5. What was not tested (or only partially testable)

- **Data Import file upload:** Actual CSV file selection and upload could not be exercised via browser MCP (browser security prevents setting file inputs programmatically). Preview Import button works; full flow (choose file → preview → import) must be tested manually.
