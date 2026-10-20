# How the conversion works

This page is a reference for maintainers. For the yearly workflow, follow `chiir2027_proceedings.ipynb`.

```
EasyChair export ──► proceedings.loader ──► ProceedingsExport ──► proceedings.exporters ──► eRights CSV / ACM XML / preview
 (xlsx or CSV pair)   + ConferenceConfig      (Pydantic models)                           └► proceedings.crosscheck
```

## Reading EasyChair

`read_easychair()` accepts the Excel workbook (sheets `Submissions` and `Authors`) or the CSV pair (`submission.csv` and `author.csv`), and renames known headers to one set of column names. For example, the CSV's `Organization` and `Corresponding author` become `Affiliation` and `Corresponding?`. CSVs are read as UTF-8, falling back to `mac_roman`, which some EasyChair downloads use. A corresponding author is recognised by `✔`, `yes`, `y`, `true`, `1` or `x`.

## Accepted papers and paper types

A submission is included when its `Decision` matches one of `accepted_decisions`, ignoring case. Its paper type comes from the first `CategoryRule` whose column contains any of the `contains` strings and all of the `contains_all` strings (ignoring case). An accepted paper that matches no rule is reported as an `uncategorised` error and left out of every file. Papers are grouped by paper type, in the order of `paper_types`. The event tracking number is that type's prefix followed by the EasyChair submission number (`fp42`), so it stays the same across re-exports.

## Author order

EasyChair's author rows are not reliably in author order. The order comes from the `Authors` column of the submission (`"A, B and C"`), with each row matched by its full name, or a partial match if needed. An author who can't be matched goes last and is reported as an `author_order_mismatch` warning. If there is no `Authors` column, the row order is used and an info notice says so.

## Contact author

Exactly one contact author per paper, chosen in this order:

1. the **first** author marked corresponding who has an email
2. otherwise, the first author with an email (warning `contact_author_priority_2`)
3. otherwise, the first author (error `contact_author_priority_3`)

When several authors are marked corresponding, `multiple_corresponding` names the person who will receive ACM's emails. The CHIIR 2026 converter passed every flag through, so ACM emailed the last one marked.

## Filling gaps across papers (multi-affiliation)

The same person is identified by first name, last name and email. Empty email, country, affiliation or web page fields are filled from that person's other papers. Existing values are **never** overwritten, because an author can legitimately have different affiliations on different papers.

## Affiliation checks

TAPS prints the eRights affiliation in the paper heading. `affiliation_detail_problems()` warns (`affiliation_too_detailed`) about affiliations that are likely to print badly:

- three or more comma-separated parts, or a department followed by a university
- address words or postcodes
- the author's country repeated at the end
- `;`, `/` or `&`, which may mean several institutions are combined
- an email or URL
- more than 100 characters

Optional canonicalisation with `affiliations_mapping.json` replaces whole affiliation strings (rules in [affiliations_mapping_rules.md](affiliations_mapping_rules.md)). Each replacement is recorded as an `affiliation_canonicalised` notice.

## Severity levels

| Severity | Meaning | Examples |
|---|---|---|
| error | Must be fixed; the export exits with status 1 | `uncategorised`, `no_authors`, `contact_author_priority_3` |
| warning | Should be reviewed | `affiliation_too_detailed`, `multiple_corresponding`, `invalid_email`, `name_consistency` |
| info | Usually legitimate | same name with different emails, `affiliation_canonicalised` |

An invalid email never drops the author. The email is left blank and an `invalid_email` warning is recorded.

## Outputs

- **eRights CSV**: the 36-column ACM Enhanced CSV format with no header row (as in 2026), one file per paper type plus `All-Papers`. The corresponding-author column is `Y`/`N`, and dates use `DD-MON-YYYY`.
- **ACM XML**: the Sheridan `erights_record` format with nested `<affiliations><affiliation><institution>…`.
- **Heading preview**: one block per paper, showing each author's affiliation and email as they will be uploaded, and marking the contact author.

## Cross-checks

After each export, `check_xml_against_source()` re-reads the raw EasyChair export and confirms that:
- the XML contains exactly the accepted, categorised papers
- the author order matches `Submissions.Authors`
- institutions and countries match the author rows
- each paper has one contact author

`check_erights_csv()` confirms that every row has 36 columns and each paper has one `Y`. `validate_acm_xml.py` (package `proceedings/validation`, documented in its README) adds deeper analysis: similar affiliation spellings, the same author under different names, and statistics.
