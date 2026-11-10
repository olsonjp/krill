# Krill UX/QA Findings — Breast Cancer Research Perspective

**Date:** 2026-02-01  
**Retest:** 2026-02-01 (after template syntax fix in `left_sidebar.html`); full workflow validation completed.

---

## Tester context

- **Role:** Biological scientist specializing in breast cancer research
- **Focus:** UX and QA testing: terminology and workflows for lab/biobank use
- **Method:** Browser MCP (cursor-browser-extension), credentials **admin:admin**
- **Scope:** No application code was changed; findings are documentation only.

---

## Executive summary

- **Retest (after template fix):** All major workflows were exercised in the browser. Login, Dashboard, Samples (list and detail), Aliquots list, Storage (Sites), Reports dashboard, Admin (User Management, Data Import), Settings, and Logout all work as expected.
- **Login** with admin:admin succeeded; redirect to home; Dashboard shows “Welcome to Krill”, stats (Active Samples 67, Storage Usage 47%, Reports 0, Alerts 0), Recent Activity, and Quick Actions.
- **Terminology** observed in-browser: Sample, Source, Experiment, Access Level (All Lab Members), Aliquot Type (e.g. Cells), Disposition (Stored, Exhausted), Quantity; Storage (Sites, Devices, Shelves, Boxes); Reports (Total Reports, Pending, Active Alerts, Storage Audit); Admin (User Management, Create User, Audit Log, Permissions, Data Import, System Admin); Settings (Display Name, Change Password, Dark Mode).
- **Remaining issues** (from codebase review and prior test): Recent Activity links in `home.html` use wrong URL patterns; Data Import disposition wording vs model; Cell Line vs Sample in docs/UI (see Issues below).

---

## 1. Terminology review

Assessment from codebase and templates (and DATA_IMPORT.md), from a breast cancer / biobank perspective.

| Term | Where seen | Assessment |
|------|------------|------------|
| **Sample** | Sample model, list/detail UI, sidebar | **OK** — Standard for “parent” biospecimen/cell line. Clear. |
| **Source** | Source model, DATA_IMPORT (Source column), sidebar “Sources” | **OK** — Used as origin (lab, study). DATA_IMPORT aligns. |
| **Cell Line** | DATA_IMPORT.md CSV column “Cell Line” | **Inconsistent** — Import uses “Cell Line”; UI uses “Sample”/“Samples”. For breast cancer (cell lines common), consider clarifying that “Sample” can represent a cell line and/or adding “Cell line” in UI labels or help text. |
| **Aliquot** | Aliquot model, list/detail, sidebar “Aliquots” | **OK** — Standard; “Aliquot Types” is clear. |
| **Tube** | AliquotTube, tube_detail, DATA_IMPORT (tubes within aliquots) | **OK** — “Tube” used appropriately for physical vial. |
| **Disposition** | AliquotDisposition (Stored, In Use, Exhausted, Disposed) | **Inconsistent** — DATA_IMPORT.md lists “In Storage”, “Used”, “Checked Out”; model uses “Stored”, “In Use”, “Exhausted”, “Disposed”. Import mapping or docs should align with model choices. |
| **Access level** | Sample/Aliquot (Admins Only, Admins & Managers, All Lab Members) | **OK** — Clear tier labels. |
| **Site / Device / Shelf / Rack / Box** | Storage hierarchy, DATA_IMPORT | **OK** — “Device” in UI vs “Freezer” in docs is acceptable (device is generic). |
| **Report types** | reports/models.py | **OK** — Sample Inventory, Storage Capacity, User Activity, Aliquot Tracking, Storage Audit are understandable. |
| **Active Samples / Storage Usage / Alerts / Recent Activity** | home.html, Dashboard | **OK** — Labels verified in-browser; stats and Quick Actions work. |
| **Tissue type / receptor status / FFPE** | — | **Missing** — No domain-specific fields for breast cancer (e.g. ER/PR/HER2, tissue type, FFPE vs frozen). Acceptable for a generic LIMS; consider as future enhancement if targeting breast cancer studies. |

---

## 2. Workflow validation

| Workflow | Status | Notes |
|----------|--------|--------|
| **1. Sign-in** | **Pass** | Navigated to `/login/`, entered admin/admin, submitted; redirect to `/`; Dashboard loads. |
| **2. Login → Dashboard** | **Pass** | Home shows Welcome to Krill, stats (Active Samples 67, Storage Usage 47%, Reports 0, Alerts 0), Recent Activity (“No recent activity”), Quick Actions (New Aliquot, Find Aliquot, Generate Report, Settings). All links resolve. |
| **3. Samples flow** | **Pass** | Sidebar Samples → list: “Samples”, “Browse and manage samples”, 67 samples, Search/Sort/Order, Create New Sample. View → sample detail (e.g. CELL_04H5: Source, Experiment, Notes, Access Level). Aliquots submenu → “Aliquots”, 871 aliquots, Sort By (Name, Sample, Type, Disposition), Create New Aliquot; cards show Sample, Disposition (Stored/Exhausted), Quantity. |
| **4. Storage flow** | **Pass** | Storage → Sites: “Sites”, “Browse and manage sites”, 1 site (Default Site), Create New Site. Sidebar shows Sites, Devices, Shelves, Boxes. |
| **5. Create sample/aliquot** | **Partial** | Create New Sample / Create New Aliquot buttons present and reachable; form submission not exercised. |
| **6. Reports** | **Pass** | Reports Dashboard: “Generate reports, manage alerts, and track system activity”; Total Reports 0, Pending 0, Active Alerts 0, Storage Audit Available; Quick Actions (Search Samples, View Alerts, Storage Audit, All Reports); Recent Reports / Recent Alerts empty. |
| **7. Admin (User Management, Data Import, etc.)** | **Pass** | Admin section expanded; User Management loads (1 user, admin, Lab Administrator, Active); Data Import loads (Upload CSV, expected format: Source;Cell Line;Experiment #;…;Disposition). Audit Log, Permissions, System Admin links present. |
| **8. Settings** | **Pass** | Settings: User Preferences (Display Name, Change Password), System Settings (Dark Mode checkbox), Save Changes. |
| **9. Logout** | **Pass** | Logout button clicked; redirect to `/login/` with login form; session ended. |

---

## 3. Issues and recommendations

1. **TemplateSyntaxError in `left_sidebar.html` (line 23)** — **Resolved.** (Previously blocked all post-login pages; fix confirmed in retest.)

2. **Recent Activity links in `home.html` do not match URL patterns**  
   - **What:** `navigateToActivity()` uses `/samples/${targetId}/` for samples and `/samples/aliquots/${targetId}/` for aliquots. The app’s URLconf uses `/samples/detail/<type>/<pk>/` and `/samples/tube/<pk>/` (sample app urls.py). Clicking a sample or aliquot from Recent Activity would 404.  
   - **Severity:** **Major**  
   - **Recommendation:** Update the JavaScript to use the real routes, e.g. `/samples/detail/sample/${targetId}/` for samples and `/samples/tube/${targetId}/` for aliquots (or use Django-rendered URLs from a data attribute / template variable).

3. **Data Import disposition values vs model**  
   - **What:** DATA_IMPORT.md documents “In Storage”, “Used”, “Checked Out”; AliquotDisposition uses “Stored”, “In Use”, “Exhausted”, “Disposed”. Data Import UI shows expected format including “Disposition” but does not list allowed values.  
   - **Severity:** **Major**  
   - **Recommendation:** Align CSV documentation and import logic: either map the documented labels to the model choices or change model/UI to match the documented terms so breast cancer lab staff can import without guessing.

4. **“Cell Line” (import) vs “Sample” (UI)**  
   - **What:** CSV column is “Cell Line”; UI speaks of “Samples” and “Create New Sample”. Data Import expected format correctly shows “Cell Line”.  
   - **Severity:** **Minor**  
   - **Recommendation:** Add a short note in the UI or DATA_IMPORT that a Sample can represent a cell line (or specimen type), so the mapping is explicit for breast cancer users.

---

## 4. Positive findings

- **Login page:** Clear “Welcome to Krill” heading, Username/Password fields and Log In button; form submitted and authenticated successfully; redirect to Dashboard.
- **Dashboard:** Welcome to Krill, Laboratory Information Management System; stats (Active Samples, Storage Usage, Reports, Alerts); Recent Activity; Quick Actions (New Aliquot, Find Aliquot, Generate Report, Settings). All links work.
- **Sidebar:** Dashboard, Samples (expandable: Samples, Aliquots, Aliquot Types, Sources), Storage (Sites, Devices, Shelves, Boxes), Reports, Settings, Admin (User Management, Create User, Audit Log, Permissions, Data Import, System Admin), Logout. Navigation is clear and consistent.
- **Samples / Aliquots:** List and detail views show Source, Experiment, Notes, Access Level (samples); Sample, Disposition (Stored/Exhausted), Quantity (aliquots). Sort/filter and Create New buttons present. Sample detail URL confirmed as `/samples/detail/sample/<pk>/`.
- **Storage:** Sites list and hierarchy (Sites, Devices, Shelves, Boxes) are discoverable; “Default Site” and Create New Site work.
- **Reports:** Dashboard with Total/Pending Reports, Active Alerts, Storage Audit; Quick Actions and empty states are clear.
- **Admin:** User Management (search, roles, table); Data Import (CSV upload, expected format with Source;Cell Line;…;Disposition) aligns with DATA_IMPORT.md column names.
- **Settings:** User Preferences (Display Name, Change Password), Dark Mode toggle, Save Changes.
- **Logout:** Single click; redirect to login; session cleared.
- **Terminology:** Core terms (Sample, Source, Aliquot, Aliquot Type, Disposition, Storage hierarchy, Lab Administrator) are consistent with common LIMS/biobank usage and appropriate for a generic lab.

---

## 5. Appendix: Pages and URLs

- **Retest (after template fix) — visited:**  
  - `http://127.0.0.1:8000/login/` — redirect to `/` (already logged in).  
  - `http://127.0.0.1:8000/` — Dashboard (Welcome to Krill, stats, Recent Activity, Quick Actions).  
  - `http://127.0.0.1:8000/samples/list/` — Samples list (67 samples, Search, Sort, Create New Sample).  
  - `http://127.0.0.1:8000/samples/detail/sample/23/` — Sample detail (CELL_04H5, Source, Experiment, Notes, Access Level).  
  - `http://127.0.0.1:8000/samples/list/?type=aliquot` — Aliquots list (871 aliquots, Disposition, Quantity).  
  - `http://127.0.0.1:8000/storage/list/?type=site` — Sites list (Default Site, Create New Site).  
  - `http://127.0.0.1:8000/reports/` — Reports Dashboard (Total/Pending Reports, Alerts, Storage Audit, Quick Actions).  
  - `http://127.0.0.1:8000/users/users/` — User Management (1 user, admin, Lab Administrator).  
  - `http://127.0.0.1:8000/users/data-import/` — Data Import (CSV upload, expected format).  
  - `http://127.0.0.1:8000/settings/` — Settings (Display Name, Change Password, Dark Mode).  
  - Logout → `http://127.0.0.1:8000/login/` — Login form.

- **Credentials used:** username `admin`, password `admin`.

- **Environment:** Django 5.0.1, runserver on 127.0.0.1:8000; tester context: biological scientist, breast cancer research, Browser MCP. Retest date: 2026-02-01.
