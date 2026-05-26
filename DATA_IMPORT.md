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

## CSV Format Requirements

### File Format
- **Delimiter**: Auto-detected — comma (`,`), semicolon (`;`), tab (`\t`), or pipe (`|`) all work
- **Encoding**: Auto-detected — UTF-8, UTF-8 with BOM (Excel default), UTF-16, or Latin-1
- **Header Row**: Required (first row must contain column names)

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
| `Position 2` | Yes* | Shelf identifier | "F" |
| `Position 3` | No | Row position within the box (1-based) | "1" |
| `Position 4` | No | Column position within the box (1-based) | "5" |
| `Aliquot Type` | Yes | Type of aliquot | "Cells", "DNA", "RNA" |
| `Number of Aliquots Total` | Yes | Total number of tubes/aliquots | "6" |
| `Disposition` | Yes | Current status of the aliquot | "stored", "in_use", "exhausted", "disposed" (or legacy aliases) |

\* Required if you want to assign storage locations. If omitted, samples will be imported without storage assignments.

### Optional Alternative Column Names

- `Collef Aliquots Total` - Alternative name for `Number of Aliquots Total` (handles typos in source data)

## Column Details

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
3. **Shelf**: Created from `Position 2`
4. **Rack**: Created from `Position 1`
5. **Box**: Created with name `{Position 1}_{Position 2}` (e.g., "4_F")

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

