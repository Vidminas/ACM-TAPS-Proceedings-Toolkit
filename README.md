# CHIIR Proceedings Tools

Tools to assist the **Proceedings Chair** with the full proceedings workflow:

1. **`convert.py`** — Convert EasyChair accepted-paper data into ACM eRights CSV files
2. **`generate_toc.py`** — Generate a cumulative-page-number Table of Contents from the ACM TAPS metadata export
3. **`front_matter_template.docx`** — Editable Word template for the proceedings front matter

---

## Requirements

```bash
pip install pandas openpyxl
```

Python 3.10 or later is required (the scripts use the `list[str]` type hint syntax).

---

## Overview of the Full Proceedings Workflow

Below is the end-to-end process.  The scripts and template slot into **Steps 2, 5, and 6**.

```
Step 1 │ Export accepted-paper data from EasyChair
Step 2 │ Run convert.py  →  upload CSV files to ACM eRights system
Step 3 │ Authors complete eRights agreements
Step 4 │ Authors upload camera-ready PDFs to ACM TAPS
Step 5 │ Run generate_toc.py on the TAPS metadata export
Step 6 │ Complete front_matter_template.docx and submit to ACM
```

---

## Step 1 — Export data from EasyChair

You need **two CSV exports** from EasyChair.  Both are found under:

> **Submissions → Download**

| File | EasyChair option | Rename to |
|---|---|---|
| Submission metadata | *All Submissions (CSV)* | `submission.csv` |
| Author details | *Authors (CSV)* | `author.csv` |

> **Important:** EasyChair exports use `mac_roman` encoding by default on some
> browsers/OS combinations.  If you encounter encoding errors, re-export using
> a different browser or re-save the file as UTF-8 in a text editor.

---

## Step 2 — Run `convert.py`

```bash
python convert.py submission.csv author.csv <EVENT_ID>
```

`EVENT_ID` is the numeric ACM event ID provided in your eRights confirmation
email (e.g. `3726522`).  The script will refuse to run without it.

### What it produces

| File | Contents |
|---|---|
| `CHIIR-<YEAR>-Full-Papers.csv` | Research articles |
| `CHIIR-<YEAR>-Short-Papers.csv` | Short papers |
| `CHIIR-<YEAR>-Demonstrations.csv` | Demo papers |
| `CHIIR-<YEAR>-Doctoral-Consortium.csv` | DC papers |
| `CHIIR-<YEAR>-Tutorials.csv` | Tutorials |
| `CHIIR-<YEAR>-Workshops.csv` | Workshop papers |
| `CHIIR-<YEAR>-All-Papers.csv` | All of the above combined |

Each file follows the **36-column ACM Enhanced CSV format (2024+)**.

### What counts as "accepted"

The script includes papers with decision **`accept`** or **`probably accept`**.
A decision breakdown is printed to the terminal so you can verify the counts
before uploading.

### Categorisation logic

Papers are categorised using the *Form Fields* and *Track Name* columns from
EasyChair.  If a paper is accepted but cannot be categorised, a `WARNING` is
printed — investigate and manually assign those papers before uploading.

The current categorisation rules are:

| Condition (checked in order) | Category |
|---|---|
| Form field contains `(Category) Full Paper` / `Resource Paper` / `Perspective` | Full Paper |
| Form field contains `(Category) Demonstration` | Demonstration |
| Form field contains `(Category) Short Paper` | Short Paper |
| Track name contains `dc` | Doctoral Consortium |
| Track name contains `short` | Short Paper |
| Track name contains `tutorial` | Tutorial |
| Track name contains `workshop` | Workshop |
| Track name contains `pc` | Full Paper |

If EasyChair track naming changes in a future year, update the conditions
in `parse_submission_csv()`.

### Updating for a new year

At the top of `convert.py`, update the `YEAR` variable:

```python
YEAR = "2027"
```

---

## Step 3 — Authors complete eRights

Upload the generated CSV files to the ACM eRights system:

1. Log in at <https://erightsreview.acm.org>
2. Navigate to your event
3. Upload each per-category CSV file (or the combined file if the system accepts it)
4. Authors will receive automated emails prompting them to sign their agreements

Monitor completion.  Authors **must** complete eRights before their papers are
processed by TAPS.

---

## Step 4 — Authors upload to TAPS

Once eRights is complete, authors receive TAPS invitations.  They upload
their source files (LaTeX or Word) and TAPS generates production-ready PDFs.

As Proceedings Chair you will need to:

- Chase authors who miss the TAPS deadline
- Review and approve papers flagged by TAPS quality checks
- Note the final `PDFPAGES` value assigned to each paper (used in Step 5)

---

## Step 5 — Run `generate_toc.py`

Once all papers are approved in TAPS, download the **metadata export**:

> ACM TAPS admin panel → **Export Metadata** → `ExportMetadata.xlsx`

Then run:

```bash
python generate_toc.py ExportMetadata.xlsx chiir2026_toc
```

This produces:

| File | Contents |
|---|---|
| `chiir2026_toc.txt` | Human-readable TOC with dot leaders and cumulative page numbers |
| `chiir2026_toc.csv` | Structured version (title, authors, start/end page, page count) |

### Expected Excel columns

| Column | Description |
|---|---|
| `ORDER ID` | Integer defining the proceedings sequence |
| `PAPER TYPE` | Category label (e.g. `Full Paper`, `Short Paper`) |
| `TITLE` | Paper title (HTML entities are decoded automatically) |
| `FIRST AUTHOR` | First/corresponding author name *(optional — included if present)* |
| `OTHER AUTHORS` | `Name!~!Affiliation!;!Name2!~!Affiliation2…` delimited string |
| `PDFPAGES` | Integer page count for this paper |

### Verifying the TOC

Check the CSV output:
- Do paper types appear in the expected order?
- Are page counts plausible (full papers typically 10–12 pp, short 4 pp, etc.)?
- Are all author names clean (no stray HTML entities or encoding artefacts)?

---

## Step 6 — Complete the front matter and submit to ACM

A pre-formatted Word template is included in this repo:

```
front_matter_template.docx
```

This covers all required front matter sections.  Open it in Microsoft Word and
fill in the highlighted placeholders for your edition of CHIIR.

### Sections in the template

| Section | What to fill in |
|---|---|
| Cover page | Conference name, year, dates, location, ISBN |
| Welcome message | General Chairs' preface |
| Organising committee | Names and affiliations per role |
| Programme committee | Names and affiliations |
| Sponsor acknowledgements | Logos and names of sponsors |
| Table of Contents | Paste from `chiir_toc.txt` (generated in Step 5) |

### Tips

- The TOC generated by `generate_toc.py` is plain text — copy it into the
  TOC section of the template and apply the `TOC Entry` paragraph style for
  consistent formatting.
- Page numbers in the TOC refer to the proceedings PDF, not the Word document
  page numbers — make sure Word's own page numbering is turned off for that
  section.
- Confirm the required file format with your ACM proceedings coordinator
  before submitting (some years require PDF, others accept the `.docx` directly).

Refer to your ACM contact for the exact submission deadline and any
institution-specific cover page requirements.

---

## File structure

```
chiir-proceedings-tools/
├── convert.py                  # EasyChair → ACM eRights CSV converter
├── generate_toc.py             # TAPS metadata → Table of Contents generator
├── front_matter_template.docx  # Editable Word template for proceedings front matter
├── README.md                   # This file
└── requirements.txt            # Python dependencies
```

### `requirements.txt`

```
pandas>=1.5
openpyxl>=3.0
```

---

## Troubleshooting

### `UnicodeDecodeError` when parsing `submission.csv`

EasyChair can export files in `mac_roman` encoding.  `convert.py` tries
UTF-8 first and falls back to `mac_roman` automatically.  If you still get
errors, open the file in a text editor (e.g. VS Code) and re-save as UTF-8.

### A paper is accepted but not categorised

`convert.py` prints a `WARNING` for any accepted paper that does not match
any categorisation rule.  Check the track name and form fields for that
paper in EasyChair and update the rules in `parse_submission_csv()` if
necessary, or manually add the paper ID to the appropriate list.

### `Missing required columns` error from `generate_toc.py`

The TAPS export column names may change between ACM platform versions.
Open the Excel file and verify the column headers match those listed in
the *Expected Excel columns* table above.  Update the column name constants
in `generate_toc.py` if needed.

### Page numbers look wrong in the TOC

- Check that `ORDER ID` values in the TAPS export reflect the correct
  intended proceedings order.  Re-order in the TAPS admin panel if needed
  before re-exporting.
- Verify that `PDFPAGES` values have been finalised (TAPS sometimes shows
  a provisional count before the paper is fully processed).

---

## Contact

Maintained by the CHIIR Proceedings Chair.  For questions about ACM systems
(eRights, TAPS, front matter submission), contact your assigned ACM
proceedings coordinator directly.
