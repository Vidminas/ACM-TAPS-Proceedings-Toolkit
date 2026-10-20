# Validation package

This package analyzes ACM XML files. It finds problems in the data, finds similar affiliation names, finds authors with more than one identity and calculates statistics. The script `validate_acm_xml.py` uses this package.

## Summary of the rules

- **Field completion:** If an author has more than one paper, the package fills empty fields from the other papers. It never replaces a value that is not empty.
- **Author identity:** The same email (upper case and lower case ignored) identifies one person. The same full name also identifies one person if one or more of the records has no email. The same name with two different emails identifies **two** persons.
- **Similar affiliations:** The package uses three steps: known aliases, then email domains, then string similarity.
- **Countries:** The package uses the `pycountry` library to change country codes and abbreviations to full names.
- **Statistics:** The package merges the identities of each author before it counts. Thus, it counts each person one time.

## Commands

| Task | Command |
|---|---|
| Examine one XML file | `python validate_acm_xml.py chiir2027.xml` |
| Write reports to files | `python validate_acm_xml.py chiir2027.xml --output chiir2027_report` |
| Show the top 10 items in each list | `python validate_acm_xml.py chiir2027.xml --top_k 10` |
| Show all items in each list | `python validate_acm_xml.py chiir2027.xml --top_k full` |
| Examine more than one file, with combined statistics | `python validate_acm_xml.py full.xml short.xml demo.xml --output combined` |
| Look at the statistics interactively | `python validate_acm_xml.py chiir2027.xml --interactive` |
| Fill empty author fields in the file | `python validate_acm_xml.py chiir2027.xml --complete-fields` |
| Fill empty author fields and write a new file | `python validate_acm_xml.py chiir2027.xml --complete-fields --complete-output completed.xml` |

**CAUTION:** Without `--complete-output`, `--complete-fields` changes the input file. Keep a copy of the file before you use this option.

The `--output PREFIX` option writes these files:

- `PREFIX_validation.txt`: the problems in the data and the validation result
- `PREFIX_statistics.txt`: the statistics, in tables
- `PREFIX_similar_affiliations.txt`: the groups of similar affiliations
- `PREFIX_merged_authors.txt`: the authors with more than one identity

The `--output` option needs the `tabulate` library.

## Modules

| Module | Contents |
|---|---|
| `checks.py` | Author identity (`merge_author_identities`, `find_merged_authors`), field completion (`complete_author_fields`), checks of names and emails (`check_name_capitalization`, `check_email_name_consistency`), similar affiliations (`find_similar_affiliations`, `merge_similar_affiliation_counts`) and functions that print the results |
| `statistics.py` | `generate_statistics`, `print_statistics`, `normalize_country_name`, `calculate_author_score` |
| `aggregation.py` | `merge_statistics` and `merge_quality_stats` combine the results of more than one file |

## Use from Python

```python
import xml.etree.ElementTree as ET
from proceedings.validation import (
    check_email_name_consistency, check_name_capitalization, complete_author_fields,
    find_similar_affiliations, generate_statistics, merge_statistics, print_statistics,
)

tree = ET.parse("chiir2027.xml")
root = tree.getroot()

name_issues = check_name_capitalization(root)       # [{"paper_id", "author_name", "field", "issue", ...}]
email_issues = check_email_name_consistency(root)   # emails used with different names
groups = find_similar_affiliations(root)            # [{"affiliations": [...], "match_type": ...}]

stats = generate_statistics(root)
print_statistics(stats, root=root)                  # root adds the merged affiliation counts

# Combine the statistics of more than one file
combined = merge_statistics([generate_statistics(ET.parse(f).getroot())
                             for f in ["full.xml", "short.xml"]])

# Fill empty fields, then write a new file
counts = complete_author_fields(root)  # affiliations_added, countries_added, departments_added
tree.write("completed.xml", encoding="utf-8", xml_declaration=True)
```

## Field completion

Some authors have more than one paper. Their data can be complete in one paper and incomplete in a different paper. The function `complete_author_fields()` fills the empty fields. It does these steps:

1. It identifies each person with `merge_author_identities()`.
2. It collects the affiliations of each person from all papers.
3. If an author record has no affiliation, it adds all known affiliations of that person. It merges the known values of each institution, so that a department or country that is not empty has priority.
4. If an author record has an affiliation, it fills only an empty department or country of the same institution.

The function puts each new affiliation in the `<affiliations>` element, as the ACM XML format requires.

The function **never** replaces a value that is not empty. An author can change institution, department or country between papers.

Examples:

```
Paper 1: John Smith (john@mit.edu), MIT, Computer Science, United States
Paper 2: John Smith (john@mit.edu), MIT, Computer Science, [empty]
Result:  Paper 2 gets "United States".

Paper 1: John Smith (john@mit.edu), MIT, USA
Paper 2: John Smith (john@mit.edu), Stanford, USA
Result:  No change. The two affiliations are correct.
```

Do not use field completion if you must keep the export exactly as it is.

## Author identity

The same person can occur more than one time in the data, with different emails, with no email, or with a different form of the name. The function `merge_author_identities()` merges these records in two steps:

1. **Same email.** All records with the same email (upper case and lower case ignored) are one person. The names can be different, for example `John Smith` and `J. Smith`.
2. **Same full name and an empty email.** The function examines the records that remain. Records with the same first name and last name are one person if one or more of them has no email. The comparison of names is exact.

These records are **not** merged:

- The same name with two different emails that are not empty, for example `Jane Doe <jane@stanford.edu>` and `Jane Doe <jane@berkeley.edu>`. These are probably two persons.
- Similar names that are not the same, for example `John Smith` and `Jon Smith`. The function does not use approximate matches, because these can give incorrect merges.

The function selects one record of each group as the canonical record. It prefers a record that has an email. If there is more than one such record, it selects the first record in alphabetical sequence. Thus, the result is always the same.

After the merge, the statistics count each paper only one time for each person.

## Checks of names and emails

- `check_name_capitalization()` finds first names and last names with a first character that is not an upper-case letter. It ignores empty names.

  **NOTE:** Some scripts, for example Chinese, have no capital letters. Names in these scripts also show as problems. Ignore these results.
- `check_email_name_consistency()` finds emails that occur with two or more different names. It ignores empty emails. It compares the full names exactly.

## Similar affiliations

The same institution can occur with different capital letters, punctuation, abbreviations or extra words. For example: `RMIT University` and `Royal Melbourne Institute of Technology`, or `University of Melbourne` and `The University of Melbourne`.

The function `find_similar_affiliations()` makes groups of similar affiliations in three steps. Each affiliation goes into one group only.

1. **Known aliases.** The function compares each affiliation with the lists in `INSTITUTION_ALIASES`. If two or more affiliations are aliases of the same institution, they become one group (`match_type="known_alias"`).
2. **Same email domain.** The function collects the email domains of the authors of each affiliation. It ignores public email services (`PUBLIC_DOMAINS`, for example `gmail.com`, `qq.com` and `acm.org`). It removes subdomains such as `student.`, `mail.` and `staff.`. Two affiliations with the same domain become one group (`match_type="email_domain"`) if one of these conditions is true:
   - They are known aliases.
   - They have one or more distinctive words that are the same.
   - Their string similarity is 0.4 or more.
3. **String similarity.** The function compares the affiliations that remain. Two affiliations become one group (`match_type="string_similarity"`) if all these conditions are true:
   - The shorter name has at least half the length of the longer name.
   - Their string similarity is equal to or more than `similarity_threshold` (default 0.8).
   - Their distinctive words overlap by 0.3 or more, or their string similarity is 0.9 or more.

In all steps, the function never merges two affiliations that are in `INSTITUTION_BLACKLIST`.

**Distinctive words** are the words of the affiliation (in lower case, without punctuation) that are not general words. These are the general words: the, university, of, college, institute, institution, school, academy, technology, science, sciences, research, center, centre, laboratory, lab, department, dept, faculty, and. If no word remains, the function uses the first word. Distinctive words prevent incorrect groups, for example `Dalian University of Technology` and `Delft University of Technology`.

**String similarity** is the ratio from Python `difflib.SequenceMatcher`. The value is between 0 and 1, where 1 means that the strings are the same.

**Why the email domain is important:** Authors of one institution usually have the same email domain. For example, `@rmit.edu.au` identifies RMIT University. The check of words or similarity in step 2 prevents incorrect groups when an author gives an incorrect email domain.

For the statistics, the function `choose_representative_affiliation()` selects one name for each group. It prefers short names, names without a department prefix, and then the first name in alphabetical sequence.

## Countries

The function `normalize_country_name()` changes country data to a full country name. It accepts these forms:

- Full names, for example `United States`
- ISO 3166-1 codes with two or three letters, for example `US`, `GB`, `USA`, `CHN`
- Abbreviations with periods, for example `U.S.`, `U.K.`, `U.A.E.`
- Usual alternative names

It uses `pycountry` for the official names. Then it changes some official names to their usual names, for example `Korea, Republic of` → `South Korea` and `Russian Federation` → `Russia` (`name_overrides` in `statistics.py`). If it cannot identify a country, it keeps the original text.

## Statistics

`generate_statistics()` merges the author identities first. Then it counts:

- Papers for each track and paper type
- Papers for each author
- Authors and papers for each affiliation and each country
- The authors with the most papers

For each affiliation and country, the statistics give two numbers:

- **Author count:** the number of author records. An author with three papers counts three times.
- **Paper count:** the number of different papers.

The ratio of the two numbers shows the size of the teams.

When you combine more than one file, the author counts are added. Each paper counts one time only, also if it occurs in more than one file.

**Author score:** The list of authors with the most papers uses a score. Each paper gives `1 + weight / 10` points. The weights are in `PAPER_TYPE_WEIGHTS` in `statistics.py`. A full paper has the weight 5. The weight of a paper type that is not in the list is `DEFAULT_PAPER_WEIGHT` (3).

## Configuration

Change these values in the code if the results are not correct:

| Value | File | Use |
|---|---|---|
| `INSTITUTION_ALIASES` | `checks.py` | Add names that are aliases of one institution. The key is the canonical name and the value is a set of aliases. Write all names in lower case. |
| `INSTITUTION_BLACKLIST` | `checks.py` | Add sets of institutions that must never be in one group, for example `{"alibaba group", "ant group"}`. Write all names in lower case. |
| `PUBLIC_DOMAINS` | `checks.py`, in `extract_email_domain()` | Add email services that do not identify an institution. |
| `subdomain_prefixes` | `checks.py`, in `normalize_email_domain()` | Add subdomains that an institution uses for some of its emails. |
| `name_overrides` | `statistics.py`, in `normalize_country_name()` | Add official country names that you want to show with their usual names. |
| `PAPER_TYPE_WEIGHTS` | `statistics.py` | Change the weight of each paper type for the author score. |
