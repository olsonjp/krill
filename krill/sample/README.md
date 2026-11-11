# Samples and aliquots

A **sample** is a cell line or other specimen. An **aliquot** is one portion of it. This page covers finding things in the lists.

## Searching the Aliquots list

Open **Samples > Aliquots**. The toolbar is one row: a search box, **Sample**, **Passage**, **More filters**, **Search** and **New Aliquot**.

### Search everything
The first box looks in every field (sample name, experiment, notes, type, disposition, passage, lab member, sample date, box, freezer and aliquot number). Type several words and **every word must match something**, so `hela p8` finds the p8 aliquots of HeLa. Put words in "quotes" to match them as one phrase. A number, with or without `#`, also matches the aliquot number.

### Search by field
Fill in a field to aim at it. **Every field you fill in must match**, so Sample `HeLa` with Passage `P8` gives only the P8 aliquots of HeLa.

| Field | Where | How it matches |
|---|---|---|
| Sample | toolbar | part of the sample name, ignoring case; every word must appear |
| Passage | toolbar | **exactly**, ignoring case: `P8` finds `P8` and `p8`, not `P80`. End with `*` to match the start: `P8*` finds `P8`, `P80`, `P8+3` |
| Lab member | More filters | part of a name, username or initials |
| Date from / Date to | More filters | on or after, and on or before. The same date in both means that day. Aliquots with no sample date are never included, and the page says how many were left out |
| Location | More filters | part of a freezer or box name |
| Aliquot number | More filters | the exact number, with or without `#` |
| Disposition, Type | More filters | pick one |

**More filters** opens by itself when one of its fields is in use, and shows how many are.

### Chips, clearing and sharing
Each active filter shows as a chip under the toolbar, for example "Passage is P8". Click its **x** to remove just that one. With two or more chips, **Clear all** removes every filter, the search words and the pills, and keeps how the list is sorted. When nothing matches, the page lists the filters in use, each with a link that removes it.

The search is kept in the page address, so you can bookmark it or send the link. The field parameters are `f_sample`, `f_passage`, `f_member`, `f_date_from`, `f_date_to`, `f_location` and `f_number`, plus the existing `disposition`, `aliquot_type` and `q`.

### Pills
Two on/off pills sit under the toolbar: **Checked out by me** (with a count) and **Hide exhausted**. They combine with everything above.

## Searching the Samples list
The Samples list has the search box plus **Source**, **Experiment** and **Notes** fields (all part-of matches), the **Low count** pill, and the same chips and Clear all.

## For developers
Each list describes its filter fields once in `sample/list_filters.py` (a `FilterSpec`: name, label, kind, hint, inline or in the More panel). From that one description come the query filters, the inputs (`templates/sample/_filter_fields.html`), the chips and Clear all (`_filter_chips.html`) and the empty-result suggestions. To add a field to a list, add a `FilterField`; to give another list the same bar, define a spec for it and call `spec.apply` and `spec.bind` from its view. Treat the parameter names as stable, because people bookmark them. Tests are in `sample/tests/test_field_filters.py`.
