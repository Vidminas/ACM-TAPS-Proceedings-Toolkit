# ACM TAPS Proceedings Toolkit

Tools for a **Proceedings Chair** taking accepted papers from EasyChair through ACM eRights and TAPS to the front matter, set up for **CHIIR 2027**.

**Start here: [`chiir2027_proceedings.ipynb`](chiir2027_proceedings.ipynb).** It is the runbook. It walks through the season in order and explains each step where you need it. Everything that changes from year to year (decisions, paper types, category rules, event ID, dates, committee layout) is set in the step that uses it.

| Step in the notebook | What it produces |
|---|---|
| 1–3 Load and check the EasyChair export | Decision breakdown, papers per type, issues to fix before ACM sees the data |
| 4 Ask authors to check their heading | Per-paper heading preview plus an email template |
| 5 Create the eRights upload | 36-column eRights CSV files (per type and combined), ACM XML, cross-checks, accepted-papers `.docx` |
| 6 Re-issue one paper | CSV/XML for a single paper after it has been pulled from TAPS/eRights |
| 7 Table of contents | Cumulative-page TOC from the TAPS `ExportMetadata.xlsx` |
| 8 Front matter | Merged and cleaned committee lists as `.docx`, plus the front-matter template |

## Setup

Python 3.10+.

```bash
python -m venv .venv
```

```bash
.venv/bin/pip install -r requirements.txt
```

```bash
.venv/bin/nbstripout --install
```

The last command makes git strip notebook outputs, which contain author names and emails, so they are never committed. Keep EasyChair and TAPS exports **outside the repository** (the notebook defaults to `~/CHIIR2027-proceedings`). `.gitignore` also ignores spreadsheets, CSV, XML and Word files as a safety net.

To try everything on invented data:

```bash
.venv/bin/python tests/fixtures/make_fixtures.py ~/CHIIR2027-demo
```

Then set `DATA_DIR = Path.home() / "CHIIR2027-demo"` in step 1 of the notebook.

## Lessons from previous CHIIR chairs (built in)

- **TAPS prints the eRights data, not the camera-ready source.** Affiliations, emails and addresses in the paper heading come from eRights. If an author puts too much into a field, the heading comes out wrong, and fixing it means removing the paper from TAPS and its eRights form. So the toolkit:
  - flags over-detailed affiliations (`affiliation_too_detailed`)
  - produces a heading preview to send authors *before* the eRights upload
  - gives a re-issue path for the 1–2 papers that will still go wrong
- **One contact author, the first one marked.** Authors often mark several corresponding authors. ACM used to email the last one, usually a senior author who doesn't respond. Now the first marked author with an email is the contact, and papers with several marked are listed.
- **Expect to repeat instructions.** The email template in step 4 is meant to be sent more than once.

## Command line

The notebook's last cell saves the conference settings as JSON and prints the matching command, so the export can be repeated without Jupyter. For example:

```bash
python easychair_export.py --config chiir2027.json --input submission.csv author.csv --format csv --event_id 1234567 --submission_date 15-OCT-2026 --approval_date 01-DEC-2026 --output out/
```

Other formats are `--format xml --proceeding_id 2027-CHIIR`, `--format preview`, and `txt`/`md` (plain lists). `--paper_id N` exports one paper only. Every export is cross-checked against the raw EasyChair data, and the command exits with status 1 on errors.

| Script | Purpose |
|---|---|
| `easychair_export.py` | EasyChair → eRights CSV / ACM XML / preview / lists |
| `validate_acm_xml.py` | Deeper analysis of ACM XML: contact authors, similar affiliations, merged identities, statistics (`--interactive`, `--output`) |
| `generate_toc.py` | TAPS `ExportMetadata.xlsx` → TOC `.txt`/`.csv` |
| `scan_referees.py` | Merge and clean committee spreadsheets (`--layout` for this year's files, `--mappings affiliations_mapping.json`) |
| `referees_to_docx.py` | Committee sheets → front-matter `.docx` (`--section "SHEET=Heading:"`) |
| `papers_to_docx.py` | ACM XML → accepted-papers list `.docx` for the website |

## Repository layout

```
chiir2027_proceedings.ipynb   runbook (start here)
proceedings/                  library: config, models, loader, exporters, crosscheck, validation/
*.py                          command-line scripts (table above)
affiliations_mapping.json     optional affiliation canonicalisation map
templates/                    CHIIR 2026 front matter, as a starting point
docs/                         how-it-works.md and reference notes
tests/                        pytest suite; fixtures/ generates invented EasyChair/TAPS data
```

Run the tests with `.venv/bin/python -m pytest tests`. [`docs/how-it-works.md`](docs/how-it-works.md) explains the conversion rules: author order, contact-author choice, multi-affiliation handling, affiliation checks and cross-checks.

## Troubleshooting

- **No accepted papers found.** The decision labels differ from `ACCEPTED_DECISIONS` in step 2. The printed decision breakdown shows the exact labels.
- **`uncategorised` error.** Add or adjust a `CategoryRule` in step 2 for the paper's track or form field.
- **`UnicodeDecodeError`** should not happen any more (CSV falls back to `mac_roman`). If it does, re-save the CSV as UTF-8.
- **`Missing required columns` from the TOC step.** TAPS column names have changed. Compare the Excel headers with `generate_toc.py`.
- **TOC page numbers look wrong.** Check `ORDER ID` and `PDFPAGES` in TAPS, then export again.

Maintained by the CHIIR Proceedings Chair. For questions about ACM systems (eRights, TAPS, front matter), contact your ACM proceedings coordinator.
