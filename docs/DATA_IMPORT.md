# Data Import Guide

This guide explains how to structure CSV files for importing sample data into Krill.

## Overview

Krill supports importing sample data via CSV files. The import process creates:
- **Sources**: Sample sources/origins
- **Samples**: Cell lines or sample types
- **Storage Hierarchy**: Sites → Devices (freezers) → Shelves → Racks → Boxes
- **Aliquots**: Individual sample aliquots
- **Tubes**: Individual tubes within aliquots
- **Locations**: Physical storage positions within boxes

## File Format Requirements

Upload either a **CSV** or an **XLSX** workbook. For XLSX only the **first sheet** is read; blank rows are skipped, formulas are read as their last saved value, and legacy `.xls` files must be re-saved as `.xlsx` or CSV. The sections below describe the CSV details; an XLSX is treated as the same table of columns.

### Importing into a database that already has data
The import adds to what is already in Krill. It never overwrites or renames existing records:
- **Matched by exact name and reused:** sources, aliquot types, dispositions and sites. **Cell lines** are matched ignoring upper/lower case and surrounding spaces (`MM134`, `mm134` and `MM134 ` are the same sample); a new sample keeps the first spelling seen in the file. Freezers are matched by name within their site, and the `Canes` shelf, racks and boxes by name within their freezer. The preview lists what was matched ("Matched to existing records") and only counts the genuinely new ones.
- **Existing records are left as they are.** An existing sample keeps its notes; new aliquots are attached to it.
- **Anything not matched is created** alongside the existing data, so a freezer or site spelled differently from the one already in Krill becomes a second, separate freezer. Use the same `Site` and `Freezer Name` as in Krill to add to an existing one.
- **Storage slots are never double-booked.** If a slot is already occupied (by existing data, or by two rows of the file), the import stops before changing anything and lists the slots.
- Importing the same file twice is therefore refused; to replace data, remove it first (for example `manage.py wipe_samples`).
- To replace an old freezer layout with the one in your sheet, remove it first with `manage.py delete_storage --site 'Old Site'` (or `--freezer 'Old Freezer'` for one freezer). It deletes the site or freezer with its shelves, racks and boxes, is a dry run unless you add `--yes`, and refuses while any aliquot is still stored in those boxes (run `wipe_samples` first). Take a database backup before using either command.

### Linking lab members to users
`Lab Member` initials are stored as written. To link them to user accounts after an import, map initials to usernames:

```
uv run python manage.py link_lab_members                                     # list initials not linked yet
uv run python manage.py link_lab_members --map MS=matt.sikora --map JS=joe.sottnik          # dry run
uv run python manage.py link_lab_members --map MS=matt.sikora --map JS=joe.sottnik --yes     # link
```
Initials match in any case, only aliquots that are not linked yet are touched, and the recorded initials are kept (the aliquot shows the user's name once linked, the initials otherwise). Re-running is safe, and any unrecognized username stops the command before anything changes.

### Rows that are skipped
A row is skipped when it has **no value in any column except** `Site`, `Freezer Name`, `Position 1`-`4` and `Aliquot Type`. These are typically empty slots listed in a pre-filled box grid. The import preview shows how many rows were skipped. A row with any other value (for example only a passage number or lab member) is still imported. Skipped slots can be added later in Krill if a tube is found there.

A row with **no cell line and no location** (no site, freezer or positions) is also skipped. These are comments typed into the sheet, such as "COMPLETE BOX H MISSING" in the `Experiment #` column. A row that has a cell line but no location is still imported.

### File Format
- **Delimiter**: Auto-detected — comma (`,`), semicolon (`;`), tab (`\t`), or pipe (`|`) all work
- **Encoding**: Auto-detected — UTF-8, UTF-8 with BOM (Excel default), UTF-16, or Latin-1
- **Header Row**: Required (first row must contain column names). Column names are matched case-insensitively and ignore surrounding spaces, so `cell line` and `CELL LINE` both work.

### Required Columns

The CSV file must include the following columns (in any order):

| Column Name | Required | Description | Example |
|------------|----------|-------------|---------|
| `Source` | Yes | Name of the sample source/origin | "Example Lab" |
| `Cell Line` | Yes | Name/identifier of the cell line or sample | "MM134" |
| `Experiment #` | No | Experiment identifier | "EXP_001" |
| `Sample Notes` | No | Notes about the sample | "Legacy sample from 2017" |
| `Site` | No | Name of the storage site/location | "Main Lab", "Satellite Facility" |
| `Freezer Name` | Yes* | Name of the freezer/storage device | "Freezer A" |
| `Position 1` | Yes* | Rack identifier | "4" |
| `Position 2` | Yes* | Box letter on the cane | "F" |
| `Position 3` | No | Row position within the box (1-based) | "1" |
| `Position 4` | No | Column position within the box (1-based) | "5" |
| `Aliquot Type` | Yes | Type of aliquot | "Cells", "DNA", "RNA" |
| `Number of Aliquots Total` | Yes | Total number of tubes/aliquots | "6" |
| `Disposition` | Yes | Current status of the aliquot | "stored", "in_use", "exhausted", "disposed" (or legacy aliases) |
| `Passage Number` | No | Passage when the aliquot was frozen, stored as written on the aliquot | "p8", "p20EV p39+4-5" |
| `Lab Member` | No | Initials of who prepared the aliquot | "JS" |
| `Sample date` | No | Date the aliquot was prepared | "2019-11-01", "7/2021" |

\* Required if you want to assign storage locations. If omitted, samples will be imported without storage assignments.

### Optional Alternative Column Names

- `Collef Aliquots Total` - Alternative name for `Number of Aliquots Total` (handles typos in source data)

## Column Details

### Passage Number, Lab Member and Sample date
These describe each individual aliquot (not the cell line) and are stored on the aliquot:
- **Passage Number** is kept as text exactly as written, since values are not always plain numbers.
- **Lab Member** is stored as the initials from the sheet. An aliquot can also be linked to a user account later (aliquot edit form); Krill shows the user's name when linked and the initials otherwise.
- **Sample date** accepts `YYYY-MM-DD`, `M/D/YYYY`, `M/D/YY`, `Mon-YY` and month-only values such as `7/2021` (stored as the 1st of the month). A date that is not understood (for example `4/38/23`, or a year alone) is left blank and counted in the import preview. Prefer the XLSX, which keeps real dates.

### Source
- Creates a new Source record if it doesn't exist
- If empty, defaults to "Unknown"
- Used to group related samples

### Cell Line
- Creates a new Sample record if it doesn't exist
- If the same Cell Line appears multiple times, notes are appended (not overwritten)
- This is the primary identifier for samples

### Experiment #
- Optional experiment identifier
- Stored with both Sample and Aliquot records

### Sample Notes
- Free-form text notes about the sample
- If the same Cell Line appears multiple times, notes are concatenated with newlines

### Site
- Optional column to specify the storage site/location
- If provided, creates a new Site record if it doesn't exist
- If omitted or empty, defaults to "Default Site"
- Useful for multi-site organizations or when importing data from different locations

### Storage Hierarchy (Site, Freezer Name, Position 1, Position 2)

The storage hierarchy is built automatically:

1. **Site**: Created from `Site` column, or defaults to "Default Site" if not provided
2. **Device (Freezer)**: Created from `Freezer Name`
3. **Shelf**: One shelf named `Canes` per freezer (a dewar has a single shelf)
4. **Rack** (a cane): Created from `Position 1`
5. **Box**: Named `{Position 1}_{Position 2}` (e.g., "4_F"). New boxes are 9x9 and grow only if a position in the sheet is larger. Existing boxes are never resized

**Note**: All storage objects are created automatically if they don't exist. Duplicate names are reused.

### Position 3 and Position 4
- **Position 3**: Row number within the box (1-based integer)
- **Position 4**: Column number within the box (1-based integer)
- Both must be provided together to create a storage location
- If omitted, aliquots are imported without specific box positions

### Aliquot Type
- Creates a new AliquotType record if it doesn't exist
- Examples: "Cells", "DNA", "RNA", "Plasma", etc.

### Number of Aliquots Total
- Determines how many tubes are created for this aliquot
- Must be a positive integer
- Each tube gets a sequential tube number (1, 2, 3, ...)
- If empty or invalid, defaults to 1

### Disposition
- Current status of the aliquot
- The column must be present, but a blank value defaults to "In Storage" (e.g. for an audit export where every tube is in the freezer)
- Creates a new AliquotDisposition record if it doesn't exist
- Accepted values:

  | CSV value | Disposition type |
  |-----------|-----------------|
  | `stored` | stored |
  | `in_use` | in_use |
  | `exhausted` | exhausted |
  | `disposed` | disposed |
  | `"In Storage"` *(legacy)* | stored |
  | `"Used"` *(legacy)* | exhausted |
  | `"Checked Out"` *(legacy)* | in_use |
  | `"Disposed"` *(legacy)* | disposed |

- Any unrecognised value defaults to `stored`
- Use the short model values (`stored`, `in_use`, etc.) for new imports; legacy aliases are still accepted for backwards compatibility

## Example CSV File

Comma-delimited (works with most editors and Excel "Save As CSV"):

```csv
Source,Cell Line,Experiment #,Sample Notes,Site,Freezer Name,Position 1,Position 2,Position 3,Position 4,Aliquot Type,Number of Aliquots Total,Disposition
Example Lab,MM134,,Legacy sample from 2017,Main Lab,Freezer A,4,F,1,1,Cells,6,In Storage
Example Lab,MM134,,Legacy sample from 2017,Main Lab,Freezer A,4,F,1,2,Cells,6,Checked Out
```

Semicolon-delimited (also accepted):

```csv
Source;Cell Line;Experiment #;Sample Notes;Site;Freezer Name;Position 1;Position 2;Position 3;Position 4;Aliquot Type;Number of Aliquots Total;Disposition
Example Lab;MM134;;Legacy sample from 2017;Main Lab;Freezer A;4;F;1;1;Cells;6;In Storage
```

**Note**: The `Site` column is optional. If omitted, all samples will be assigned to "Default Site".

## Import Process

### Access Requirements
- You must have the `lab_manager` role or higher to import data
- Access the import page via: **User Management → Data Import**

### Import Steps

1. **Prepare your CSV file** following the format above
2. **Upload the file** using the import form
3. **Review the preview** (if dry-run is enabled)
4. **Confirm the import** to create records in the database

### What Gets Created

For each row in your CSV:

1. **Source** (if new)
2. **Sample** (if new, based on Cell Line)
3. **Storage Hierarchy** (if storage columns provided):
   - Site → Device → Shelf → Rack → Box
4. **AliquotType** (if new)
5. **AliquotDisposition** (if new)
6. **Aliquot** (one per row)
7. **AliquotTubes** (one per `Number of Aliquots Total`)
8. **AliquotLocation** (if Position 3 and Position 4 provided)

### Duplicate Handling

- **Sources**: Same name = same source (reused)
- **Samples**: Same Cell Line = same sample (notes appended)
- **Storage**: Same names = same objects (reused)
- **AliquotTypes**: Same name = same type (reused)
- **AliquotDispositions**: Same name = same disposition (reused)
- **Aliquots**: Each row creates a new aliquot (even if same sample)

## Common Issues and Solutions

### Issue: "Missing required columns" error
**Solution**: Ensure your CSV header row exactly matches the column names (case-sensitive). The error message lists the missing columns alongside what was actually found, so you can quickly spot typos or extra spaces.

### Issue: Samples imported but no storage locations
**Solution**: Ensure `Freezer Name`, `Position 1`, and `Position 2` are provided. `Position 3` and `Position 4` are optional but both must be present together.

### Issue: Wrong number of tubes created
**Solution**: Check the `Number of Aliquots Total` column. It must be a positive integer. Empty values default to 1.

### Issue: Disposition not recognized
**Solution**: Use one of these exact values in the CSV: `"In Storage"`, `"Used"`, `"Checked Out"`, or `"Disposed"`. Other values will default to `stored` status. Note: these are the CSV-level labels; internally the model stores disposition types as `stored`, `in_use`, `exhausted`, or `disposed`.

### Issue: Import fails with encoding errors
**Solution**: The importer auto-detects encoding (UTF-8, UTF-8 with BOM, UTF-16, Latin-1), so most files — including those exported from Excel — work without changes. If you still see errors, try re-saving the file as UTF-8 from your spreadsheet application.

## Tips for Large Imports

1. **Test with a small file first** (5-10 rows) to verify format
2. **Use consistent naming** for Sources, Freezer Names, and Aliquot Types
3. **Group related samples** by using the same Source name
4. **Verify storage hierarchy** before importing large datasets
5. **Keep backups** of your original CSV files

## Data Validation

The import process performs basic validation:
- Required columns are checked
- Numeric fields are validated (Position 3, Position 4, Number of Aliquots Total)
- Storage positions must be positive integers
- Empty strings are converted to empty values or defaults

## After Import

After importing:
1. Verify samples appear in the **Samples** list
2. Check storage locations in the **Storage** section
3. Review aliquots in sample detail pages
4. Check audit logs for import history

## Support

If you encounter issues with data import:
1. Check this guide for format requirements
2. Verify your CSV matches the example format
3. Check the application logs for detailed error messages
4. Contact your system administrator

