# Exhibit finder for the Tashkent Polytechnic Museum

This tool finds and ranks retired museum exhibits that fit the Tashkent Polytechnic Museum. The museum covers automotive and transport technology, engineering, mechanics, physics, electricity, optics, robotics, industrial technology, STEM education, interactive science and the history of technology.

It does **not** collect every object that happens to be available. Each candidate goes through the
**Tashkent Polytechnic Museum relevance check**. Anything not relevant is removed from the database and listed in a separate rejection log with the reason.

> Optimise for *how many genuinely useful exhibits the museum can acquire*, not *how many objects were found*.
> Ten relevant retired interactive exhibits are worth more than 500 random deaccessioned objects.

Python 3.9+, standard library only.

```bash
# 1. Generate targeted search queries (Group A by default; add B with --groups A B)
python -m exhibit_finder queries --csv queries.csv

# 2. Record what research finds in a candidates JSON file (see data/example_candidates.json)

# 3. Run the relevance check and build the shortlist
python -m exhibit_finder check data/example_candidates.json --out out
#   out/database.json   kept candidates, sorted HIGH -> LOW
#   out/database.md     readable shortlist
#   out/rejected.json   NOT_RELEVANT (and WEAK_MATCH unless --include-weak): "DO NOT RECOMMEND"

python -m unittest discover -s tests
```

## Museum relevance

The relevance category is decided by rules: what the object *is* and which profile concepts it demonstrates. There is no numeric score.

| Value | Rule |
|---|---|
| `DIRECT_MATCH` | Demonstrates a **Group A** concept: automotive (A1), transport (A2), interactive physics: mechanics, fluids, waves, optics, electricity (A3), robotics and automation (A4), engineering (A5), energy (A6), STEM interactive stations (A7), digital and immersive (A8), automotive manufacturing (A9) |
| `STRONG_MATCH` | Demonstrates a **Group B** concept: aviation, railway, industrial or agricultural machinery, telecoms, electronics, computing history, materials, environment, space |
| `RELATED` | A technology object (machine, apparatus, instrument…) outside those categories |
| `WEAK_MATCH` | A **Group C** object type (book, document, poster, photo, furniture, clothing, memorabilia…) with a real technology-history connection, or a toy or souvenir version of a technology object |
| `NOT_RELEVANT` | Excluded types (art, archaeology, natural history, coins…), Group C types with no technology connection, or nothing technological. Never shown as a candidate. |

**What the object is** comes from `object_type` when it is given; otherwise the title's head noun is used. "Photograph of a locomotive" is a photograph, "railway timetables" are timetables, and "Engine cutaway with posters" is an engine cutaway. Fill in `object_type` to remove any ambiguity.

The full taxonomy, including every concept, its search phrases, and what it teaches visitors, is in [`exhibit_finder/profile.py`](exhibit_finder/profile.py). Curators can edit that file without touching any logic.

## WHY_IT_FITS_TASHKENT_POLYTECHNIC_MUSEUM

Every kept candidate gets a concrete statement of what it demonstrates and which museum areas it serves. For example:

> Interactive Engine Cutaway demonstrates piston movement, combustion and power transmission inside an internal combustion engine… Fits the museum's automotive technology, engineering … and interactive science areas.

A researcher can write their own `why_it_fits`. It is kept only if it is specific: at least 60 characters, names a profile area, mentions what the object demonstrates, and uses no generic wording such as "interesting for the museum". If it fails, it is replaced and the problems are recorded in `why_it_fits_rejected`.

## Acquisition priority

Priority is **not** based on availability alone. There are five factual criteria, and each one is `true`, `false` or unknown:

1. genuine museum exhibit (on display at a museum or science centre, now retired)
2. physically reusable (`condition`: working or complete)
3. educational value (follows from relevance)
4. reasonable logistics (`logistics_reasonable`)
5. current availability confirmed (offered **and** backed by an `evidence_url`; a status of on display, sold or scrapped means `false`)

| Priority | Rule |
|---|---|
| `HIGH` | `DIRECT_MATCH`/`STRONG_MATCH` and all five criteria true |
| `MEDIUM` | `DIRECT_MATCH`/`STRONG_MATCH` and exactly one criterion still unknown |
| `LOW` | weaker relevance, any criterion false, or two or more unknown |

## Ideal target

`IDEAL_TARGET` is true only when the object meets all of these: an old museum exhibit, replaced or retired, currently available with evidence, `DIRECT_MATCH`, photos or documentation, a contact person, and international transfer possible. Any missing items are listed in `ideal_target_gaps`, which works as the to-do list for the next email to the institution.

## Candidate record

See [`exhibit_finder/models.py`](exhibit_finder/models.py) for the full field list and the allowed values. Unknown fields are rejected, so typos cannot pass silently.

```json
{
  "id": "EX-001",
  "title": "Interactive Engine Cutaway",
  "object_type": "engine cutaway",
  "description": "Visitor-operated sectioned petrol engine ...",
  "source_institution": "Science Centre X",
  "source_type": "science_centre",
  "history": "Installed in 2012; replaced in 2026 during gallery renovation",
  "exhibit_status": "FOR_TRANSFER",
  "status_date": "2026-09-01",
  "evidence_url": "https://...",
  "evidence_type": "official_museum_document",
  "condition": "working",
  "photos_available": true,
  "contact_name": "...", "contact_email": "...",
  "international_transfer": "yes",
  "logistics_reasonable": true
}
```

The records in `data/example_candidates.json` are the two worked examples from the requirements, using placeholder institutions. They are not real offers.

## Where to look

There is no central marketplace for retired science-centre exhibits, so the generated queries combine three things:

- a concrete concept (e.g. `"engine cutaway" OR "cutaway engine"`)
- the wording institutions use when exhibits leave the gallery (`"exhibits for sale"`, `"decommissioned exhibit"`, `"gallery renovation" "old exhibits"`, …)
- the type of institution that owns real exhibits (science centre, technology, transport or automotive museum)

Books, paintings, posters, archives and toys are excluded with negative terms. The best leads usually come from science centres announcing gallery renewals, from institutions that develop exhibits (for example, the California Science Center lists exhibits for rent and sale), and from direct contact through the ASTC and Ecsite networks.
