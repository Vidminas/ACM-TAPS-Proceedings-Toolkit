# Referee data cleanup

The script `scan_referees.py` cleans the committee data. It does this after it reads each `.xlsx` and `.csv` file in the input folder. It cleans the data before it compares the files and before it writes `referees.xlsx`.

The general rules (spaces, capital letters, rows and files) **always** apply. The affiliation replacements come from the file `affiliations_mapping.json`. They apply **only** if you give `--mappings PATH`. Without this option, the script does not change the affiliations.

The script compares each affiliation with the keys of the mapping file. The comparison uses the full string, without spaces at the start and end. It ignores upper case and lower case. If no key agrees, the affiliation does not change.

## Commands

To do only the general cleanup, use this command:

```bash
python scan_referees.py
```

To do the general cleanup and the affiliation replacements, use this command:

```bash
python scan_referees.py --mappings affiliations_mapping.json
```

The JSON file has this structure: `{"affiliations": {"<lowercase from>": "<to>", ...}}`. To add, remove or change a replacement, edit this file. It is not necessary to change the code.

## General rules

These rules always apply:

| Scope | Rule |
|---|---|
| Excel lock files | The script ignores files with names that start with `~$`. Excel makes these files when a workbook is open. |
| Empty rows | The script removes rows that have no first name, last name, email or profile. |
| Profile column | If the `profile` column contains an email and the `email` column is empty, the script copies the profile to the `email` column. |
| Spaces | The script changes each sequence of spaces, tabs and line breaks to one space. It removes spaces at the start and end of each cell. Empty cells (`NaN` or `None`) become `""`. Thus, the mapping keys do not need versions with line breaks. |
| Capital letters of names | The script changes the first name, middle name and last name to title case only if the cell is fully in lower case or fully in upper case. It does not change names with mixed case, for example `de Vries` or `McDonald`. |
| Track chairs | The script keeps records with the role `track chair` for the comparisons. It does not write them to `referees.xlsx`. The comparison of the role ignores upper case and lower case. |
| Merged output | In each sheet of `referees.xlsx`, the rows are in alphabetical sequence by last name, then first name, then affiliation. The sequence ignores upper case and lower case. |

## Affiliation replacements

The list of replacements is in `affiliations_mapping.json`. For the rules of its entries, see [affiliations_mapping_rules.md](affiliations_mapping_rules.md).
