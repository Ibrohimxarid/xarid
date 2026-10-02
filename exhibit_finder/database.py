"""Evaluate candidates and build the (small, relevant) acquisition database."""

import json

from . import priority as prio
from . import relevance as rel
from .models import Candidate
from .profile import MUSEUM_NAME


def evaluate(candidate):
    r = rel.check(candidate)
    p = prio.assess(candidate, r)

    why_problems = []
    why = ""
    if r.relevance != rel.NOT_RELEVANT:
        if candidate.why_it_fits:
            why_problems = rel.validate_why_it_fits(candidate.why_it_fits, r)
            why = candidate.why_it_fits if not why_problems else ""
        why = why or rel.generate_why_it_fits(candidate, r)

    return {
        "id": candidate.id,
        "museum": candidate.source_institution,
        "location": ", ".join(x for x in (candidate.city, candidate.country) if x),
        "old_exhibit": candidate.title,
        "object_type": candidate.object_type,
        "history": candidate.history,
        "status": candidate.exhibit_status,
        "status_date": candidate.status_date,
        "evidence": {"type": candidate.evidence_type, "url": candidate.evidence_url},
        "contact": {"name": candidate.contact_name, "role": candidate.contact_role,
                    "email": candidate.contact_email},
        "photos_available": candidate.photos_available,
        "documentation_available": candidate.documentation_available,
        "international_transfer": candidate.international_transfer,
        "MUSEUM_RELEVANCE": r.relevance,
        "relevance_reason": r.reason,
        "profile_categories": list(dict.fromkeys(f"{m.category_code} {m.category_name}" for m in r.matches)),
        "concepts": list(dict.fromkeys(m.concept for m in r.matches)),
        "interactive": r.interactive,
        "demonstrator": r.demonstrator,
        "WHY_IT_FITS_TASHKENT_POLYTECHNIC_MUSEUM": why,
        "why_it_fits_rejected": why_problems,
        "ACQUISITION_PRIORITY": p.priority,
        "acquisition_criteria": p.criteria,
        "unmet_criteria": p.unmet,
        "open_questions": p.uncertain,
        "IDEAL_TARGET": p.ideal_target,
        "ideal_target_gaps": p.ideal_target_gaps,
    }


def _sort_key(rec):
    return (prio.PRIORITY_ORDER.index(rec["ACQUISITION_PRIORITY"]),
            rel.RELEVANCE_ORDER.index(rec["MUSEUM_RELEVANCE"]),
            not rec["IDEAL_TARGET"],
            not rec["interactive"],
            rec["old_exhibit"].lower())


def build(candidates, include_weak=False):
    """Return (database, rejected).

    NOT_RELEVANT objects are never shown to the user; they go to `rejected`
    with the reason. WEAK_MATCH is left out by default too: the database
    should contain exhibits the museum would actually acquire.
    """
    database, rejected = [], []
    for c in candidates:
        rec = evaluate(c)
        keep = rec["MUSEUM_RELEVANCE"] not in (rel.NOT_RELEVANT,) and \
            (include_weak or rec["MUSEUM_RELEVANCE"] != rel.WEAK_MATCH)
        if keep:
            database.append(rec)
        else:
            rejected.append({"id": rec["id"], "old_exhibit": rec["old_exhibit"], "museum": rec["museum"],
                             "MUSEUM_RELEVANCE": rec["MUSEUM_RELEVANCE"], "reason": rec["relevance_reason"],
                             "result": "DO NOT RECOMMEND"})
    database.sort(key=_sort_key)
    return database, rejected


def load_candidates(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        data = data.get("candidates", [])
    return [Candidate.from_dict(d) for d in data]


def _fmt_bool(v):
    return {True: "yes", False: "no", None: "unknown"}[v]


def to_markdown(database, rejected):
    out = [f"# {MUSEUM_NAME} -- exhibit acquisition shortlist", ""]
    counts = {p: sum(r["ACQUISITION_PRIORITY"] == p for r in database) for p in prio.PRIORITY_ORDER}
    ideal = sum(r["IDEAL_TARGET"] for r in database)
    out.append(f"{len(database)} candidate(s): {counts['HIGH']} HIGH, {counts['MEDIUM']} MEDIUM, "
               f"{counts['LOW']} LOW; {ideal} meet the ideal-target profile. "
               f"{len(rejected)} object(s) rejected as not relevant (see rejected list).")
    out.append("")
    out.append("| Priority | Relevance | Exhibit | Museum | Status | Ideal |")
    out.append("|---|---|---|---|---|---|")
    for r in database:
        out.append(f"| {r['ACQUISITION_PRIORITY']} | {r['MUSEUM_RELEVANCE']} | {r['old_exhibit']} | "
                   f"{r['museum']} | {r['status']} | {'yes' if r['IDEAL_TARGET'] else 'no'} |")
    for r in database:
        out += ["", f"## {r['old_exhibit']}", "",
                f"- **Museum:** {r['museum']}" + (f" ({r['location']})" if r["location"] else ""),
                f"- **History:** {r['history'] or 'not stated'}",
                f"- **Status:** {r['status']}" + (f" (as of {r['status_date']})" if r["status_date"] else ""),
                f"- **Evidence:** {r['evidence']['type'] or 'none'} {r['evidence']['url']}".rstrip(),
                f"- **Contact:** " + (", ".join(x for x in r["contact"].values() if x) or "none"),
                f"- **Museum relevance:** {r['MUSEUM_RELEVANCE']} -- {r['relevance_reason']}",
                f"- **Why it fits Tashkent Polytechnic Museum:** {r['WHY_IT_FITS_TASHKENT_POLYTECHNIC_MUSEUM']}",
                f"- **Acquisition priority:** {r['ACQUISITION_PRIORITY']}"]
        crit = ", ".join(f"{k.replace('_', ' ')}: {_fmt_bool(v)}" for k, v in r["acquisition_criteria"].items())
        out.append(f"- **Criteria:** {crit}")
        if r["ideal_target_gaps"]:
            out.append(f"- **To reach ideal target:** {'; '.join(r['ideal_target_gaps'])}")
        if r["why_it_fits_rejected"]:
            out.append(f"- **Researcher's why-it-fits rejected:** {'; '.join(r['why_it_fits_rejected'])}")
    if rejected:
        out += ["", "## Rejected (not shown as candidates)", ""]
        for r in rejected:
            out.append(f"- {r['old_exhibit']} ({r['museum'] or 'unknown source'}): "
                       f"{r['MUSEUM_RELEVANCE']} -- {r['reason']} **{r['result']}.**")
    return "\n".join(out) + "\n"
