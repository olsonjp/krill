# Simplified Directory Structure – Status and Remaining Work

This doc summarizes what was fixed and what remains after the branch that aimed to simplify the project directory structure.

## What was fixed

### 1. Test discovery (blocking)

**Problem:** `python manage.py test` failed with:

```text
ImportError: 'tests' module incorrectly imported from '.../sample/tests'.
Expected '.../sample'. Is this module globally installed?
```

**Cause:** The `sample` app had both:

- `sample/tests.py` (a 1,700+ line test module)
- `sample/tests/` (a package with `test_access_levels.py`, `test_aliquot_management.py`)

Having both a `tests` module and a `tests` package in the same app confused Django’s test discovery.

**Fix:** The package was renamed so it no longer shadows the module:

- `sample/tests/` → `sample/test_suite/`

No code imported `sample.tests` (the package), so no other changes were required. The full test suite now runs (333 tests). Remaining failures (e.g. `Aliquot() got unexpected keyword arguments: 'aliquotType'`, form validation assertions) are test/model or test/form drift, not structure issues.

---

## Current state: duplicated “krill” layout

The branch introduced a second set of templates and static assets under the **krill** package, but Django is still configured to use only the **top-level** dirs. So you effectively have two parallel layouts:

| Resource        | In use (Django settings)     | Also present (unused)        |
|----------------|-------------------------------|------------------------------|
| Base templates | `templates/` (BASE_DIR)       | `krill/templates/`           |
| Static files   | `static/krill/` (STATICFILES_DIRS) | `krill/static/krill/`  |
| Left sidebar   | `templates/base/left_sidebar.html` | `krill/templates/base/left_sidebar.html` |

- **TEMPLATES** in `settings.py`: `DIRS = [BASE_DIR.joinpath('templates')]` → only the top-level `templates/` is used.
- **STATICFILES_DIRS**: `[BASE_DIR / "static/krill"]` → only the top-level `static/krill/` is used.

So anything under `krill/templates/` and `krill/static/` is **not** loaded by Django right now.

### Template / tag mismatch

- **`krill/templates/base/left_sidebar.html`** uses `{% load sample_tags %}` and the `{% is_samples_list_active %}` tag.
- **`sample_tags`** is only defined under **`krill/sample/templatetags/sample_tags.py`**.
- The real Django app is the **top-level** `sample/`; its `sample/templatetags/` has only `__init__.py` (no `sample_tags.py`).

So:

- The **in-use** sidebar is `templates/base/left_sidebar.html`, which does **not** use `sample_tags` (different active-state logic).
- If you ever switch to `krill/templates/base/left_sidebar.html`, that template would fail unless `sample_tags` is available from the `sample` app (e.g. copy `sample_tags.py` into `sample/templatetags/`).

---

## Options for finishing the simplified setup

Pick one direction and stick to it.

### Option A: Keep current layout (top-level only)

- **Do:** Treat `krill/templates/`, `krill/static/`, and `krill/sample/` as leftovers.
- Either delete them or keep them only as reference, and do not add them to `TEMPLATES` / `STATICFILES_DIRS`.
- Ensure all shared templates and static files live under `templates/` and `static/krill/` (as today). No further config changes needed.

### Option B: Move shared UI into `krill/` and single source of truth

1. **Templates**
   - Add the krill template dir in settings, e.g.  
     `DIRS = [BASE_DIR.joinpath('templates'), BASE_DIR.joinpath('krill', 'templates')]`  
     (order decides which overrides which), or replace the first with only `BASE_DIR.joinpath('krill', 'templates')` and move all shared templates there.
   - Consolidate so there is one canonical place for `base/layout.html`, `base/left_sidebar.html`, etc. (either under `templates/` or under `krill/templates/`), and remove duplicates.

2. **Static**
   - Either point `STATICFILES_DIRS` at `krill/static/krill/` (and move any needed files from `static/krill/` into `krill/static/krill/`) or keep using `static/krill/` and remove the duplicate under `krill/static/`.

3. **`sample_tags`**
   - Copy `krill/sample/templatetags/sample_tags.py` into **`sample/templatetags/sample_tags.py`** (the real app) so that any template (including `krill/templates/base/left_sidebar.html`) can use `{% load sample_tags %}`.

4. **Cleanup**
   - Remove or repurpose the other copy (e.g. delete `krill/sample/` if it’s only a partial duplicate of the top-level `sample` app).

---

## Summary

- **Fixed:** Test discovery by renaming `sample/tests/` → `sample/test_suite/`. Tests run; remaining failures are test/model drift.
- **Still to do:** Decide whether the “simplified” layout is top-level only (Option A) or `krill/` as the single place for shared UI (Option B), then either remove the unused `krill/` copies or complete the move and wire settings + `sample_tags` accordingly.
