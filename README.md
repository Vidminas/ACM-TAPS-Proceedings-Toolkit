# ACM TAPS Proceedings Toolkit

This toolkit is for the **Proceedings Chair** of **CHIIR 2027**. It moves the data for accepted papers from EasyChair to ACM eRights and TAPS. It also makes the table of contents and the front matter.

**Start with [`chiir2027_proceedings.ipynb`](chiir2027_proceedings.ipynb).** This notebook is the procedure. Do its steps in sequence during the proceedings period. Each step contains its instructions and its settings. The settings that change each year are in the step that uses them.

| Step in the notebook | Result |
|---|---|
| 1–3 Load and examine the EasyChair export | A count of the decisions, a count of papers for each paper type, and a list of problems to correct |
| 4 Ask the authors to examine their headings | A heading preview for each paper and an email template |
| 5 Make the eRights upload | eRights CSV files with 36 columns, ACM XML, the results of the cross-checks, and a list of accepted papers (`.docx`) |
| 6 Send one paper again | CSV and XML for one paper, after ACM removes that paper from TAPS and eRights |
| 7 Table of contents | A table of contents with page numbers, from the TAPS file `ExportMetadata.xlsx` |
| 8 Front matter | Committee lists (`.docx`) and the front-matter template |

## Installation

You must have Python 3.10 or a later version.

1. Make a virtual environment:

   ```bash
   python -m venv .venv
   ```

2. Install the dependencies:

   ```bash
   .venv/bin/pip install -r requirements.txt
   ```

3. Install the `nbstripout` Git filter:

   ```bash
   .venv/bin/nbstripout --install
   ```

**WARNING:** Do not put EasyChair or TAPS exports in the repository. These files contain the names and emails of authors. Keep them in a different folder. The default folder in the notebook is `~/CHIIR2027-proceedings`.

The `nbstripout` filter removes the notebook outputs before each commit, because the outputs also contain author data. The `.gitignore` file also ignores spreadsheet, CSV, XML and Word files.

To try the toolkit with invented data, do these steps:

1. Make the invented data:

   ```bash
   .venv/bin/python tests/fixtures/make_fixtures.py ~/CHIIR2027-demo
   ```

2. In step 1 of the notebook, set `DATA_DIR = Path.home() / "CHIIR2027-demo"`.

## Lessons from the previous CHIIR chairs

The toolkit includes these lessons:

- **TAPS uses the eRights data for the paper heading.** TAPS does not use the affiliations, emails or addresses in the camera-ready source. If an author writes too much in a field, the heading is not correct. To correct the heading, ACM must remove the paper from TAPS and remove its eRights form. Thus, the toolkit does these tasks:
  - It finds affiliations that contain too much detail (`affiliation_too_detailed`).
  - It makes a heading preview. Send this preview to the authors before the eRights upload.
  - It gives a procedure to send one paper again. Use it for the one or two papers that still have problems.
- **There is only one contact author: the first author who has the corresponding mark.** Authors often mark more than one author as corresponding. Previously, ACM sent emails to the last marked author. This author was usually a senior author who did not reply. Now the contact author is the first marked author who has an email. The toolkit shows all papers that have more than one marked author.
- **Authors do not always read the instructions.** Be prepared to send the email template in step 4 more than once.

## Command line

The last cell of the notebook writes the conference settings to a JSON file. It also shows the related command. Use this command to do the export again without Jupyter. For example:

```bash
python easychair_export.py --config chiir2027.json --input submission.csv author.csv --format csv --event_id 1234567 --submission_date 15-OCT-2026 --approval_date 01-DEC-2026 --output ~/CHIIR2027-proceedings/output/
```

These are the other formats:

- `--format xml --proceeding_id 2027-CHIIR` for ACM XML
- `--format preview` for the heading preview
- `--format txt` or `--format md` for a simple list of papers

The `--output` path must be outside the repository. Use `--paper_id N` to export only paper N. The command compares each export with the EasyChair data. If it finds an error, the exit status is 1.

| Script | Function |
|---|---|
| `easychair_export.py` | Converts the EasyChair export to eRights CSV, ACM XML, a heading preview or a list |
| `validate_acm_xml.py` | Analyzes ACM XML: contact authors, similar affiliations, authors with more than one identity, statistics (`--interactive`, `--output`) |
| `generate_toc.py` | Converts the TAPS file `ExportMetadata.xlsx` to a table of contents (`.txt` and `.csv`) |
| `scan_referees.py` | Merges and cleans the committee spreadsheets (`--layout` for the files of the year, `--mappings affiliations_mapping.json`) |
| `referees_to_docx.py` | Converts committee sheets to a `.docx` file for the front matter (`--section "SHEET=Heading:"`) |
| `papers_to_docx.py` | Converts ACM XML to a `.docx` list of accepted papers for the website |

## Repository layout

```
chiir2027_proceedings.ipynb   procedure (start here)
proceedings/                  library: config, models, loader, exporters, crosscheck, validation/
*.py                          command-line scripts (see the table above)
affiliations_mapping.json     optional map of affiliation names
templates/                    CHIIR 2026 front matter, for use as a starting point
docs/                         how-it-works.md and reference documents
tests/                        pytest tests; fixtures/ makes invented EasyChair and TAPS data
```

To run the tests, use `.venv/bin/python -m pytest tests`. The document [`docs/how-it-works.md`](docs/how-it-works.md) gives the conversion rules: author sequence, contact author, more than one affiliation, affiliation checks and cross-checks.

## Troubleshooting

| Problem | Cause and remedy |
|---|---|
| The notebook finds no accepted papers. | The decision labels are not the same as `ACCEPTED_DECISIONS` in step 2. Compare them with the decision count that the notebook shows. |
| The notebook shows the error `uncategorised`. | No category rule agrees with the track or form field of the paper. Add or change a `CategoryRule` in step 2. |
| The script shows `UnicodeDecodeError`. | The CSV file has an unusual encoding. Save the CSV file again with the UTF-8 encoding. |
| The table of contents step shows `Missing required columns`. | TAPS changed the column names. Compare the Excel column names with the names in `generate_toc.py`. |
| The page numbers in the table of contents are not correct. | Examine `ORDER ID` and `PDFPAGES` in TAPS. Then export the file from TAPS again. |

## Acknowledgements

This toolkit uses the code of two earlier projects:

- [**acm-proceedings**](https://github.com/MarwahAlaofi/acm-proceedings) by Oleg Zendel and Marwah Khaled Hasan Alaofi (SIGIR proceedings, MIT License, see `LICENSE-MIT-sigir`). The EasyChair loader with validation, the ACM XML exporter, `validate_acm_xml.py`, the referee scanner and the Word exports come from this project.
- [**ACM-TAPS-Proceedings-Toolkit**](https://github.com/NeuraSearch/ACM-TAPS-Proceedings-Toolkit) by Niall McGuire and Yashar Moshfeghi (CHIIR 2026 proceedings). The eRights CSV format, the CHIIR category rules, `generate_toc.py`, the front-matter template and the procedure come from this project.

We also thank Maria Gäde. Her scripts for earlier CHIIR proceedings (EasyChair XML to ACM eRights) helped this work. This toolkit does not include code from these scripts.

The `NOTICE` file shows which files come from which project.

The CHIIR Proceedings Chair maintains this toolkit. If you have questions about the ACM systems (eRights, TAPS, front matter), speak to your ACM proceedings coordinator.
