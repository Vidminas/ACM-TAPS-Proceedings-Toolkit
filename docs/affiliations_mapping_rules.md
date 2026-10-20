# Affiliation mapping rules

The file `affiliations_mapping.json` changes affiliation names from authors and reviewers to one standard name for the proceedings. This document gives the rules for its entries.

The file has this structure:

```json
{
  "affiliations": {
    "<lowercase-from>": "<presentation-ready-to>",
    ...
  }
}
```

Two scripts can use the file:

- `scan_referees.py` uses it only if you give `--mappings PATH`. Without this option, the script only removes extra spaces and corrects the capital letters of names. It does not change affiliations.
- The paper export can also use it (`easychair_export.py --affiliation_mapping`, or `AFFILIATION_MAPPING` in step 3 of the notebook). The default is off, because TAPS prints the affiliation exactly as you upload it.

---

## Rule 1: Use the top-level organization

Change each affiliation to the **university** or the **company or institute**.

- **Remove departments.** Remove `Department of Computer Science`, `Faculty of Engineering`, `School of Information`, `Graduate School of Information Science`, `College of Information Science and Engineering`, `Dipartimento di Informatica` (an Italian department prefix) and similar text.
- **Remove countries and cities** that are not part of the name of the institution. Examples:
  - `"Tongji University, Shanghai, China"` → `"Tongji University"`
  - `"Donghua University, Shanghai"` → `"Donghua University"`
  - `"Hansung University Seoul"` → `"Hansung University"`
- **Keep campus names** that identify one campus of an institution with more than one campus. The campus name is part of the official name. If an author writes only the name of the main institution, change it to the name of the main campus. Examples:
  - `University of Maryland` / `…, College Park` → `University of Maryland, College Park`
  - `University of Michigan` / `…, Ann Arbor` / `… - Ann Arbor` → `University of Michigan - Ann Arbor`
  - `University of Minnesota` / `…, Twin Cities` / `… - Twin Cities` → `University of Minnesota - Twin Cities`
  - `University of Virginia` / `…, Charlottesville` → `University of Virginia, Charlottesville`
  - `New York University, Abu Dhabi` → `New York University Abu Dhabi`. This campus gives its own degrees. It is different from NYU New York.
  - `The University of Nottingham Ningbo China` stays the same, because it is a different campus.
- **Company suffixes: decide for each company. Use the form that most authors used.** Some entries keep legal suffixes such as `Inc.`, `Ltd.`, `LLC`, `Corp.`, `Co., Ltd.`, `LP`, `SE` and `Group`. Other entries remove them. Use the form that occurs most in the submitted data. If the counts are equal or there are no counts, use the name that the company uses for itself. If you still cannot decide, use the preference of Marwah Alaofi, from her manual edits.
  - **The brand name without a suffix**, because most authors used this form:
    - `Adobe`, `Adobe Inc.`, `Adobe Systems` → `Adobe`
    - `Apple Inc`, `Apple Inc.` → `Apple`
    - `Baidu Inc.` → `Baidu`
    - `Google LLC` → `Google`
    - `Kuaishou Tech`, `Kuaishou Technology` → `Kuaishou`
  - **The name with the suffix**, because most authors used it, or because it is the official name:
    - `Alibaba` → `Alibaba Group`
    - `Bloomberg` → `Bloomberg LP`
    - `Booking` → `Booking.com`
    - `eBay Inc` → `eBay Inc.`
    - `Huawei Technologies Co Ltd` → `Huawei Technologies Ltd.`
- **Remove an acronym in parentheses** if no submitted record uses it. There are three reasons for this rule:
  - No submitted record contains the acronym.
  - The institutions do not include their acronym in the name on their websites.
  - The manual edits of Marwah Alaofi always removed the acronym.

  Examples:
  - `Agency for Science, Technology and Research (A*STAR)` → `Agency for Science, Technology and Research`
  - `Institut National de la Recherche Scientifique (INRS)` → `Institut National de la Recherche Scientifique`
  - `Massachusetts Institute of Technology (MIT)` → `Massachusetts Institute of Technology`
  - `Mohamed bin Zayed University of Artificial Intelligence (MBZUAI)` → `Mohamed bin Zayed University of Artificial Intelligence`
  - `National Institute of Advanced Industrial Science and Technology (AIST)` → `National Institute of Advanced Industrial Science and Technology`
  - `Norwegian University of Science and Technology (NTNU)` → `Norwegian University of Science and Technology`
  - `Pohang University of Science and Technology (POSTECH)` → `Pohang University of Science and Technology`
  - `Tomorrow Advancing Life (TAL)` → `Tomorrow Advancing Life`
  - `Ulsan National Institute of Science and Technology (UNIST)` → `Ulsan National Institute of Science and Technology`
  - `Universidade Estadual de Campinas (UNICAMP)` → `Universidade Estadual de Campinas`

  **Exception:** Keep the text in parentheses if it is a campus or location name, not an acronym. Examples:
  - `Harbin Institute of Technology (Shenzhen)`
  - `Hong Kong University of Science and Technology (Guangzhou)`
  - `Qilu University of Technology (Shandong Academy of Sciences)`. Here the text in parentheses is part of the legal name after a merger.

---

## Rule 2: Keep the names of independent research organizations

Some labs or divisions are independent research organizations with a strong brand. Keep the specific name of these organizations. Do not change them to the name of the parent company.

- `Microsoft Research` and `Microsoft Research Asia` stay different from `Microsoft`.
- `Google DeepMind` stays different from `Google`.
- `Huawei Ireland Research Center` stays different from `Huawei`.
- `Facebook` and `Meta` stay different if the authors wrote them that way.

### Exception: keep the institutes of the Chinese Academy of Sciences

The named institutes of the Chinese Academy of Sciences (ICT, IIE, IA, CNIC and others) are independent research organizations with a strong brand. **Always keep their full names.** Do not change them to `Chinese Academy of Sciences`.

- `Institute of Computing Technology, Chinese Academy of Sciences` (ICT-CAS). This entry also corrects the typing errors `Institute of Computing Technolgy, ...` and `Intitute of Computing Technology, ...`.
- `Institute of Information Engineering, Chinese Academy of Sciences` (IIE-CAS)
- `Institute of Automation, Chinese Academy of Sciences` (IA-CAS)
- `Computer Network Information Center, Chinese Academy of Sciences` (CNIC-CAS)

### Exception: change general divisions to the parent company

If a division of a company is not an independent research organization, use the name of the parent company.

- Example: `"Walmart Global Tech"` → `"Walmart"`

---

## Rule 3: Join two or more organizations with " & "

Sometimes an author gives **two or more different top-level organizations**. Examples are a university and a company, or a university and an independent research institute. Keep all of them. Put ` & ` (an ampersand with one space on each side) between them.

- `"university of stavanger and google deepmind"` → `"University of Stavanger & Google DeepMind"`
- `"inesc tec and faculty of engineering, university of porto"` → `"INESC TEC & Universidade do Porto"`

This rule also applies to three organizations: `"University of Kassel & hessian.AI & ScaDS.AI"`.

---

## Rule 4: French joint research units (UMR)

A French joint research unit (UMR), for example IRIT or LIG, has two owners: a university and the national research center (CNRS). Use the names of the two owners, so that each owner gets credit.

- Example: `"institut de recherche en informatique de toulouse"` → `"Université de Toulouse & CNRS"`

---

## Rule 5: Format of keys and values

- **Write all keys in lower case.** The script compares the keys without upper case and lower case differences. Thus, each key must be fully in lower case.
- **Write each value exactly as the proceedings must show it.** Use the correct capital letters and punctuation.
- **Use one name consistently for each large international university.** This name is often in the language of the country.
  - `"University de Montreal"` / `"University of Montreal"` → `"Université de Montréal"`
  - `"Technische Universität Wien"` → `"TU Wien"`
- **Add keys for different hyphens and spaces.** The script does not correct hyphens or spaces. If the standard name has a hyphen without spaces, or a space and no hyphen, add a key for each incorrect form.
  - `"ISTI CNR"` → `"ISTI-CNR"`
  - `"University of Milano - Bicocca"` → `"University of Milano-Bicocca"`
- **Correct the capital letters of affiliations.** The script corrects the capital letters of names only. It does not correct affiliations. If an affiliation is in lower case or has incorrect capital letters, add a key with the correct value. Examples:
  - `"the university of texas at austin"` → `"The University of Texas at Austin"`
  - `"Université d'aix-Marseille, CNRS"` → `"Université d'Aix-Marseille, CNRS"`

---

## Rule 6: Old names and typing errors

- **Use the current official name.** Change old names and alternative names to the current official name.
  - `"Université Pierre et Marie Curie"` → `"Sorbonne Université"`
  - `"Beijing University of Aeronautics and Astronautics"` → `"Beihang University"`
- **Add keys for typing errors.** If a misspelled name occurs in the data, add it as a key in lower case. Then the script finds and corrects it.
  - Example: the key `"institute of computing technolgy, chinese academy of sciences"` has a value with the correct spelling.

---

## Checklist for a new entry

1. Make sure that the key is fully in lower case.
2. Make sure that the value is exactly the text for the proceedings.
3. Remove the department, the city and the country from the value. Keep the company suffix if the authors used it.
4. Keep the name of an independent research organization (Rule 2), for example ICT-CAS.
5. If the string has two or more organizations, put ` & ` between them.
6. Look for an existing key for the same affiliation. Ignore upper case and lower case. If there is such a key, add a new key with the same value. Do not change the existing value.
