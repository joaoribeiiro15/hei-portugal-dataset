# Higher Education Institutions in Portugal Dataset

## Overview

This repository produces a consolidated dataset of Portuguese higher education institutions (HEIs), which can serve as a target list for a web security measurement campaign. It combines two Excel files stored in the `Source/` folder into a single CSV file and applies a few normalization steps so that institutional attributes can be analyzed consistently.

It is the Portuguese counterpart of the Norwegian dataset built for the master's thesis _An Assessment of Web-Related Security in Norwegian Higher Education Institutions_, and is structured identically so that the two national datasets can be ingested by the same scanning pipeline and compared directly. The dataset supports the definition of target institutions and services, and enables regional analysis using NUTS codes, as required by the research questions on maturity variation and regional asymmetries.

## Repository structure

- `Source/HEIs/Portugal HEIs.xlsx`
  Enriched list of Portuguese HEIs, including categorization fields and the institutional website.

- `Source/NUTS/Portugal.xlsx`
  NUTS 2024 codes and labels used to attach regional identifiers to each institution.

- `Script/main.py`
  Interactive script that loads both sources, performs normalization and joins, and exports the final dataset.

- `pt-heis-2026.csv`
  The generated dataset, committed at the repository root. Re-running the script recreates it; the default output name in the script prompt is `pt-heis-2026.csv`.

- `LICENSE`
  Licence covering this dataset and the build script.

## How to generate the dataset

Run the script from the repository root:

```bash
python Script/main.py
```

The script prints a small file tree for `Source/HEIs` and `Source/NUTS`, marks Excel files, lets you choose which files to merge, and then prompts for an output name. Press Enter to accept the default.

## Output schema

The generated CSV contains the following columns:

- `ID`
- `Name`
- `Category`
- `Institution_Category_Standardized`
- `Member_of_European_University_alliance`
- `url`
- `NUTS2`
- `NUTS2_Label`
- `NUTS3`
- `NUTS3_Label`
- `Domain_Status`

### Column descriptions

#### Core identifiers

- **`ID`**
  Unique identifier of the institution in the HEIs source, in the format `PT-HEI-XXX`. Rows carrying a `-D01`, `-D02` suffix are organic units of the parent institution that operate their own independently administered domain.

- **`Name`**
  Official English name of the institution, with the Portuguese acronym in parentheses. Organic unit rows carry the parent name followed by the unit name.

- **`url`**
  Institutional website, used as the primary measurement target in the thesis scanning pipeline.

#### Normalized institutional attributes

- **`Category`**
  Normalized legal status, derived from the HEIs source "Legal status" definition.

- **`Institution_Category_Standardized`**
  Normalized institutional type, derived from the HEIs source "Institution Category" definition, and grounded in the Regime Juridico das Instituicoes de Ensino Superior (RJIES, Lei 62/2007) as amended by Lei 32/2026.

- **`Member_of_European_University_alliance`**
  Indicator of whether the institution is part of a European Universities Initiative alliance, based on European Commission sources.

These fields enable comparison of security posture across institution types, and exploration of whether specific organizational characteristics correlate with stronger or weaker web security configurations.

#### Regional attributes

- **`NUTS2`**, **`NUTS2_Label`**
  NUTS level 2 code and label, used to group institutions by macro region.

- **`NUTS3`**, **`NUTS3_Label`**
  NUTS level 3 code and label, used to group institutions by sub-regional subdivisions, and to support finer-grained regional comparisons.

## Conversions and normalization rules

The script converts integer codes into descriptive values so the CSV can be analyzed directly.

### Category (Legal status)

- `1` -> `Public`
- `0` -> `Private`
- `2` -> `Concordatarian`
- `3` -> `Cooperative`
- `4` -> `Public (Military/Police)`

The Portuguese system needs more than the Norwegian public/private binary. `Concordatarian` applies only to the Catholic University of Portugal, whose status derives from the Concordat between the Portuguese State and the Holy See. `Cooperative` covers institutions owned by cooperatives or foundations under private law that are not straightforwardly commercial. `Public (Military/Police)` covers the military and police subsystem governed by Decreto-Lei 249/2015.

### Institution_Category_Standardized (Institution Category)

- `1` -> `University`
- `2` -> `Non-integrated University Institute`
- `3` -> `Polytechnic Institute`
- `4` -> `Non-integrated Polytechnic School`
- `5` -> `Military and Police Higher Education Institution`

### Domain_Status

- `V` -> verified, the domain was confirmed and resolves without an unexpected redirect
- `K` -> known with high confidence, follows the institution's established naming, preflight recommended
- `U` -> unverified candidate, must be confirmed before scanning

Filter on this column before any measurement campaign. Scanning a `U` target risks measuring a parked domain, a redirect destination, or an unrelated site, which would silently corrupt the results.

### Member_of_European_University_alliance

- `1` -> `Member of a European Universities Initiative alliance`
- `0` -> `Not found in European Commission sources`

## Rows, domains, and campuses

The Portuguese landscape differs from the Norwegian one in a way that matters for a web security study: many institutions delegate web operations to faculties and schools, which run their own domains under their own administration. A single row per institution would therefore understate the attack surface by a wide margin.

The rule applied here is one row per distinct institutional domain:

- Every institution has a base row keyed `PT-HEI-XXX` pointing at its main site.
- Every organic unit with an independently administered domain has its own row, keyed `PT-HEI-XXX-D01`, `PT-HEI-XXX-D02`, and so on, inheriting the parent's category, alliance status, and NUTS codes.

Campus splits are handled differently. The companion workbook `Portugal_Universities.xlsx` splits multi-campus institutions into `PT-HEI-XXX-1`, `PT-HEI-XXX-2` sub-rows so that each campus can be attributed to its own NUTS 3 region. Those sub-rows are collapsed back to the base ID in the CSV, because the campuses share a single website and would otherwise create duplicate scan targets.

## NUTS version

All regional codes use **NUTS 2024**, established by Commission Delegated Regulation (EU) 2023/674 of 26 December 2022 and in force since 1 January 2024. Portugal has 3 NUTS 1, 9 NUTS 2, and 26 NUTS 3 regions under this version. Relative to NUTS 2021:

- The former Area Metropolitana de Lisboa was abolished and split into Grande Lisboa (PT1A) and Peninsula de Setubal (PT1B).
- A new NUTS 2 region, Oeste e Vale do Tejo (PT1D), was created from the former Oeste, Medio Tejo, and Leziria do Tejo.
- Serta and Vila de Rei moved from Medio Tejo to Beira Baixa.
- Alto Tamega was renamed Alto Tamega e Barroso.

Any comparison with a dataset built on NUTS 2021 must account for these changes, since the Lisbon region in particular is not comparable across versions.

## Legal state of the sector, August 2026

The Portuguese binary university/polytechnic system was substantially restructured in mid-2026, and this dataset reflects the post-restructuring position:

- **Lei 32/2026** of 20 July 2026, in force 1 August 2026, automatically renamed thirteen public polytechnic institutes holding unconditional A3ES institutional accreditation to `Universidade Politecnica`: Beja, Braganca, Castelo Branco, Cavado e Ave, Coimbra, Guarda, Lisboa, Portalegre, Santarem, Setubal, Tomar, Viana do Castelo, and Viseu. Their presidents become reitores; the legal nature of the teaching is unchanged.
- **Decreto-Lei 135/2026**, published in Diario da Republica on 9 July 2026, converted the Polytechnic of Leiria into the University of Leiria and Oeste. A parallel decree converted the Polytechnic of Porto into the Technical University of Porto. Both leave the polytechnic subsystem entirely.

Several of these institutions still operate their legacy `ipXX.pt` domains. That mismatch between legal name and domain is itself a useful data-quality signal and is preserved rather than smoothed over.

## Script behavior, and why it matters

The script exists to make the dataset reproducible and auditable. Instead of manually editing spreadsheets, it provides a consistent, repeatable pipeline that:

1. Loads the selected HEIs Excel file and the selected NUTS Excel file.
2. Selects the relevant fields for the output schema.
3. Applies the categorical conversions described above.
4. Merges NUTS codes and labels into the institution rows.
5. Writes a single CSV file that can be ingested by the web security scanning and analysis tooling.

In practical terms, this script matters because the study depends on a well-defined target list. The measurement campaign, covering HTTPS and TLS posture, DNSSEC adoption, and HTTP security header deployment, requires stable inputs such as a canonical domain per target and stable region labels for aggregation. A scripted build step reduces the risk of accidental inconsistencies, and supports later re-runs when the sources, or the institutional landscape, change. Given the pace of change in the Portuguese sector during 2026, that last point is not hypothetical.

## Institution universe

The institution list is the DGES registry `Pesquisa de Cursos e Instituicoes`, consulted on 10 August 2026 with no filters applied. It returned 93 institutions across three tabs: 31 public, 60 private, and 2 public military and police. Every base row in this dataset maps to exactly one registry entry, so the universe is complete and auditable rather than representative.

Three findings from that consultation changed the shape of the dataset relative to earlier drafts:

- **The autonomous nursing schools no longer exist as institutions.** Decreto-Lei 83/2024 of 31 October integrated the Escolas Superiores de Enfermagem of Coimbra, Lisbon, and Porto into the universities of those cities, retaining polytechnic nature for all other purposes. The process completed by 1 January 2026. They appear here as organic-unit rows, not as institutions.
- **The military academies are organic units of IUM.** The DGES military and police tab lists only two institutions, IUM and ISCPSI. The Naval School, Military Academy, and Air Force Academy sit beneath IUM.
- **The DGES registry does not yet reflect the 2026 restructuring.** It still lists the polytechnic institutes under their pre-2026 names, with no entry for a University of Leiria and Oeste or a Technical University of Porto. The `Name` column therefore carries the DGES name, and the companion workbook records the reported 2026 designation alongside it. Resolve this against Diario da Republica before publishing.

## Known limitations

- **Enrollment, faculty, and department counts are not in the CSV.** They live in the companion workbook `Portugal_Universities.xlsx`, and several are still self-reported rather than drawn from DGEEC per-establishment tables. See the `Sources & Notes` sheet of that workbook.
- **Organic unit domains are enumerated for six institutions only** (ULisboa, UPorto, UC, NOVA, IPLeiria, IPP). Other institutions also operate school-level domains that have not yet been confirmed. The DGES access index at https://www.dges.gov.pt/guias/indest.asp lists the organic units for every institution and is the right starting point.
- **50 of the 137 rows carry a `Domain_Status` of `K` or `U`.** Live per-domain verification through a browser required a separate authorization for each host, which was not practical for the full private sector in one pass. Preflight these before scanning.
- **ETER identifiers are not carried in the CSV** and two could not be confirmed at all. See the workbook.

## Sources and references

### HEIs

- <a href="https://www.dges.gov.pt/pt/pesquisa_cursos_instituicoes">DGES, Direcao-Geral do Ensino Superior, institutions and courses registry</a>
- <a href="https://www.a3es.pt">A3ES, Agencia de Avaliacao e Acreditacao do Ensino Superior</a>
- <a href="https://dre.pt">Diario da Republica, RJIES (Lei 62/2007), Lei 32/2026, Decreto-Lei 135/2026, Decreto-Lei 249/2015</a>
- <a href="https://eurydice.eacea.ec.europa.eu/eurypedia/portugal/higher-education">Eurydice, "Higher education" (Portugal)</a>

### Statistics

- <a href="https://www.dgeec.medu.pt">DGEEC, Direcao-Geral de Estatisticas da Educacao e Ciencia, RAIDES</a>
- <a href="https://www.ine.pt">INE, Instituto Nacional de Estatistica</a>

### European Universities Initiative (European Commission)

- <a href="https://education.ec.europa.eu/education-levels/higher-education/european-universities-initiative">European Universities Initiative</a>

### International identifiers

- <a href="https://www.eter-project.com">ETER, European Tertiary Education Register</a>
- <a href="https://data.deqar.eu">DEQAR</a>
- <a href="https://www.whed.net">IAU WHED</a>

### NUTS

- <a href="https://ec.europa.eu/eurostat/web/nuts">Eurostat, NUTS classification</a>
- <a href="https://www.ine.pt">INE, NUTS 2024 for Portugal</a>
