# How the conversion works

This document is for maintainers. For the procedure of each year, use `chiir2027_proceedings.ipynb`.

```
EasyChair export ──► proceedings.loader ──► ProceedingsExport ──► proceedings.exporters ──► eRights CSV / ACM XML / preview
 (xlsx or CSV pair)   + ConferenceConfig      (Pydantic models)                           └► proceedings.crosscheck
```

## Read the EasyChair data

The function `read_easychair()` reads one of these two inputs:

- The Excel workbook, with the sheets `Submissions` and `Authors`
- The CSV pair, `submission.csv` and `author.csv`

The function changes known column names to one set of names. For example, `Organization` in the CSV file becomes `Affiliation`, and `Corresponding author` becomes `Corresponding?`.

The function reads CSV files with the UTF-8 encoding. If this encoding does not work, it uses the `mac_roman` encoding. Some EasyChair downloads use `mac_roman`.

These values mark a corresponding author: `✔`, `yes`, `y`, `true`, `1` and `x`.

## Accepted papers and paper types

A submission is accepted if its `Decision` agrees with one of the `accepted_decisions`. The comparison ignores upper case and lower case.

The paper type comes from the first `CategoryRule` that agrees with the submission. A rule agrees when its column contains one or more of the `contains` strings and all of the `contains_all` strings. The comparison ignores upper case and lower case.

If an accepted paper agrees with no rule, the loader records the error `uncategorised`. That paper is not in the output files.

The loader puts the papers into groups by paper type. The sequence of the groups is the sequence of `paper_types`.

The event tracking number is the prefix of the paper type, followed by the EasyChair submission number. An example is `fp42`. This number does not change when you export the data again.

## Author sequence

The author rows in EasyChair are not always in the correct sequence. Thus, the loader uses the `Authors` column of the submission, for example `"A, B and C"`. It finds each author row by the full name. If the full name does not agree, it tries a partial name.

If the loader cannot find an author in the `Authors` column, it puts that author last. It also records the warning `author_order_mismatch`.

If there is no `Authors` column, the loader uses the sequence of the rows. It records a notice about this.

## Contact author

Each paper has one contact author. The loader selects the contact author in this sequence:

1. The **first** author with the corresponding mark who has an email
2. If there is no such author, the first author who has an email. The loader records the warning `contact_author_priority_2`.
3. If no author has an email, the first author. The loader records the error `contact_author_priority_3`.

If more than one author has the corresponding mark, the loader records the warning `multiple_corresponding`. This warning gives the name of the author who will receive the ACM emails.

**NOTE:** The CHIIR 2026 converter kept all corresponding marks. Thus, ACM sent its emails to the last marked author.

## Missing fields for authors with more than one paper

The loader identifies one person by the first name, the last name and the email. If a field is empty in one paper, the loader copies the value from a different paper of the same person. This applies to these fields: email, country, affiliation and web page.

The loader **never** replaces a value that is not empty. An author can have a different affiliation on each paper.

## Affiliation checks

TAPS writes the eRights affiliation in the paper heading. The function `affiliation_detail_problems()` finds affiliations that can give a bad heading. For each problem, the loader records the warning `affiliation_too_detailed`. These are the problems:

- The affiliation has three or more parts with commas between them.
- The affiliation has a department, then a university.
- The affiliation contains words from a postal address, or a postcode.
- The affiliation ends with the country of the author.
- The affiliation contains `;`, `/` or `&`. These characters can show two or more institutions in one field.
- The affiliation contains an email or a URL.
- The affiliation has more than 100 characters.

The file `affiliations_mapping.json` can replace full affiliation strings with a standard name. This function is optional. For its rules, see [affiliations_mapping_rules.md](affiliations_mapping_rules.md). The loader records each replacement as the notice `affiliation_canonicalised`.

**NOTE:** The mapping file joins two institutions with ` & `. The affiliation check gives a warning for these affiliations. This is intentional, because TAPS prints the full string.

## Severity levels

| Severity | Meaning | Examples |
|---|---|---|
| error | You must correct it. The export ends with exit status 1. | `uncategorised`, `no_authors`, `contact_author_priority_3` |
| warning | Examine it. | `affiliation_too_detailed`, `multiple_corresponding`, `invalid_email`, `name_consistency`, `missing_approval_date` |
| info | It is usually correct. | The same name with different emails, `affiliation_canonicalised` |

If an email is not valid, the loader does not remove the author. It removes the email and records the warning `invalid_email`.

## Outputs

- **eRights CSV:** This is the ACM Enhanced CSV format with 36 columns. It has no header row, the same as in 2026. There is one file for each paper type and one file, `All-Papers`, for all papers. The corresponding-author column contains `Y` or `N`. The dates use the format `DD-MON-YYYY`.
- **ACM XML:** This is the Sheridan `erights_record` format. The institution is in `<affiliations><affiliation><institution>`.
- **Heading preview:** There is one block for each paper. Each block shows the affiliation and email of each author, as the upload will show them. It also shows the contact author.

## Cross-checks

After each export, the function `check_xml_against_source()` reads the EasyChair export again. It makes sure of these conditions:

- The XML contains all the accepted papers that have a paper type, and no other papers.
- The author sequence agrees with `Submissions.Authors`.
- The institutions and countries agree with the author rows.
- Each paper has one contact author.

The function `check_erights_csv()` makes sure that each row has 36 columns and that each paper has one `Y`.

The script `validate_acm_xml.py` does more analysis. It finds similar affiliation names and authors with more than one identity. It also calculates statistics. For more data, see the README of the package `proceedings/validation`.
