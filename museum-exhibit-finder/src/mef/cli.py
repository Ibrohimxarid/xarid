"""Command-line interface: ``mef <command>``.

Discovery (needs internet):
  mef queries | search | import-results | collect | triage | fts
Knowledge base (offline):
  mef validate | dedupe | build | export | report | stats | all
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from .config import PATHS, settings


def _load_files():
    from .evidence import load_research

    res = load_research()
    for path, err in res.errors:
        print(f"✗ {path.name}: {err}", file=sys.stderr)
    return [mf for _, mf in res.files], res.errors


# ---- knowledge base -------------------------------------------------------------


def cmd_validate(args) -> int:
    from .candidates import build as build_candidates

    files, errors = _load_files()
    print(f"{len(files)} research files valid, {len(errors)} invalid")
    # Relevance check hygiene: every candidate needs a concrete WHY_IT_FITS,
    # and every itemised exhibit needs an object_type for the relevance rules.
    cands, _, _ = build_candidates(files)
    weak_why = [c for c in cands if c.why_problems]
    for c in weak_why:
        print(f"WHY_IT_FITS {c.museum.museum.id}/{c.obj.id}: {'; '.join(c.why_problems)}")
    untyped = [(mf.museum.id, it.id) for mf in files for ex in mf.exhibitions for it in ex.exhibits
               if getattr(it.object_type, "value", it.object_type) == "unspecified"]
    for mid, iid in untyped:
        print(f"object_type missing: {mid}/{iid}")
    print(f"{len(cands)} relevance-checked candidates, {len(weak_why)} with an unacceptable WHY_IT_FITS, "
          f"{len(untyped)} exhibits without object_type")
    return 1 if errors or weak_why or untyped else 0


def cmd_dedupe(args) -> int:
    from .dedupe import canonical_url, find_duplicate_museums

    files, _ = _load_files()
    pairs = find_duplicate_museums([mf.museum.model_dump() for mf in files])
    for p in pairs:
        print(f"possible duplicate museum: {p.a} ↔ {p.b} ({p.reason}, {p.score:.0f})")
    dup_urls = 0
    for mf in files:
        seen: dict[str, str] = {}
        for e in mf.evidence:
            c = canonical_url(e.url)
            if c in seen and e.claim == next(x.claim for x in mf.evidence if x.id == seen[c]):
                print(f"duplicate evidence in {mf.museum.id}: {seen[c]} = {e.id}")
                dup_urls += 1
            seen.setdefault(c, e.id)
    print(f"{len(pairs)} possible duplicate museums, {dup_urls} duplicate evidence records")
    return 1 if pairs or dup_urls else 0


def cmd_build(args) -> int:
    from .db import build, connect

    n, errors = build(connect())
    print(f"database rebuilt: {n} museums → {PATHS.db}")
    for path, err in errors:
        print(f"✗ {path.name}: {err}", file=sys.stderr)
    return 1 if errors else 0


def cmd_export(args) -> int:
    from .exporter import export_all

    files, _ = _load_files()
    for name, path in export_all(files).items():
        print(f"{name:14s} → {path.relative_to(PATHS.root)}")
    return 0


def cmd_report(args) -> int:
    from .report import generate

    files, _ = _load_files()
    run_dir = generate(files, label=args.label)
    print(f"report → {run_dir.relative_to(PATHS.root)}/REPORT.md")
    return 0


def cmd_stats(args) -> int:
    from .stats import compute_stats

    files, _ = _load_files()
    for k, v in compute_stats(files).items():
        print(f"{k:58s} {v}")
    return 0


def cmd_all(args) -> int:
    rc = cmd_validate(args)
    if rc:
        return rc
    cmd_dedupe(args)
    return cmd_build(args) or cmd_export(args) or cmd_report(args) or cmd_stats(args)


# ---- discovery ---------------------------------------------------------------------


def cmd_queries(args) -> int:
    from .search import build_queries

    qs = build_queries(args.group, args.lang, args.country, args.limit)
    for q in qs:
        print(f"[{q['group']}/{q['lang']}{'/' + q['country'] if q['country'] else ''}] {q['query']}")
    print(f"{len(qs)} queries", file=sys.stderr)
    return 0


def cmd_search(args) -> int:
    from .db import connect
    from .search import build_queries, run_search, store_results

    qs = build_queries(args.group, args.lang, args.country, args.limit)
    print(f"running {len(qs)} queries via {args.backend or settings().search.get('backend')}")
    results = run_search(qs, backend=args.backend)
    added = store_results(connect(), results)
    print(f"{len(results)} results, {added} new")
    return 0


def cmd_import_results(args) -> int:
    from .db import connect
    from .search import import_results, store_results

    results = import_results(Path(args.file))
    print(f"imported {store_results(connect(), results)} new of {len(results)} results")
    return 0


def cmd_collect(args) -> int:
    from .classifier import classify
    from .collector import fetch
    from .contacts import extract_contacts
    from .db import connect
    from .exhibits import extract_mentions
    from .parser import parse

    conn = connect()
    rows = conn.execute(
        "SELECT url, canonical_url, MAX(relevance) AS rel FROM search_results "
        "WHERE relevance >= ? AND canonical_url NOT IN (SELECT canonical_url FROM pages) "
        "GROUP BY canonical_url ORDER BY rel DESC LIMIT ?",
        (args.min_relevance, args.limit),
    ).fetchall()
    use_llm = args.llm or settings().llm.get("enabled", False)
    print(f"collecting {len(rows)} pages")
    for r in rows:
        f = fetch(r["url"])
        if f is None or f.status >= 400:
            print(f"  ✗ {r['url']}")
            continue
        page = parse(f)
        c = classify(page.url, page.text, page.title)
        contacts = [x.as_dict() for x in extract_contacts(page.text, f.final_url)]
        mentions = [m.__dict__ for m in extract_mentions(page.text)]
        cls = json.loads(c.model_dump_json())
        if use_llm and c.priority:
            from .llm import assess_page

            cls["llm"] = assess_page(page.url, page.text)
        conn.execute(
            "INSERT OR REPLACE INTO pages VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (r["canonical_url"], r["url"], f.fetched_at, f.status, f.content_type, f.via, page.title,
             page.date, page.text, json.dumps(cls, ensure_ascii=False), c.relevance, c.priority,
             json.dumps(contacts, ensure_ascii=False), json.dumps(mentions, ensure_ascii=False)),
        )
        try:
            conn.execute("INSERT INTO pages_fts VALUES (?,?,?)", (r["canonical_url"], page.title, page.text))
        except Exception:
            pass
        conn.commit()
        print(f"  {c.priority or '  '} {c.relevance:5.1f} {page.url}")
    return 0


def cmd_triage(args) -> int:
    """Group candidate pages by museum domain and write draft YAML to research/inbox/."""
    from .db import connect
    from .dedupe import registered_domain

    conn = connect()
    rows = conn.execute(
        "SELECT * FROM pages WHERE priority IS NOT NULL AND relevance >= ? ORDER BY relevance DESC",
        (args.min_relevance,),
    ).fetchall()
    by_domain: dict[str, list] = defaultdict(list)
    for r in rows:
        by_domain[registered_domain(r["url"]) or "unknown"].append(r)
    PATHS.inbox.mkdir(parents=True, exist_ok=True)
    today = dt.date.today().isoformat()
    for domain, pages in by_domain.items():
        evidence = []
        for i, p in enumerate(pages, start=1):
            cls = json.loads(p["classification"])
            mentions = json.loads(p["mentions"] or "[]")
            evidence.append({
                "id": f"e{i}", "url": p["url"], "title": p["title"] or None,
                "source_type": "other", "source_date": (p["date"] or "")[:10] or None,
                "accessed": (p["fetched_at"] or today)[:10],
                "claim": "TODO: one-sentence claim this source supports",
                "excerpt": mentions[0]["sentence"] if mentions else None,
                "excerpt_is_verbatim": bool(mentions),
                "signals": sorted(s for s in cls.get("signals", {}) if s != "contact"),
                "verified_via": "pipeline",
                "notes": f"classifier: {cls.get('priority')} relevance {cls.get('relevance')}",
            })
        draft = {
            "museum": {"id": domain.split(".")[0], "name": "TODO", "country": "TODO",
                       "website": f"https://{domain}", "type": "TODO"},
            "contacts": [
                {"email": c.get("email"), "phone": c.get("phone"), "linkedin": c.get("linkedin"),
                 "position": c.get("role"), "kind": "general", "source": pages[0]["url"]}
                for p in pages[:1] for c in json.loads(p["contacts"] or "[]")[:5]
            ],
            "exhibitions": [],
            "evidence": evidence,
            "research": {"researcher": "mef triage", "last_updated": today,
                         "next_step": "Verify evidence, fill museum card, move to research/museums/"},
        }
        out = PATHS.inbox / f"{domain}.yaml"
        out.write_text(yaml.safe_dump(draft, sort_keys=False, allow_unicode=True), encoding="utf-8")
        print(f"draft → {out.relative_to(PATHS.root)} ({len(pages)} pages)")
    return 0


def cmd_fts(args) -> int:
    from .db import connect

    conn = connect()
    for r in conn.execute(
        "SELECT canonical_url, snippet(pages_fts, 2, '[', ']', '…', 12) AS s FROM pages_fts "
        "WHERE pages_fts MATCH ? LIMIT ?", (args.query, args.limit)
    ):
        print(f"{r['canonical_url']}\n    {r['s']}")
    return 0


def cmd_classify_text(args) -> int:
    from .classifier import classify
    from .contacts import extract_contacts
    from .exhibits import extract_mentions

    text = Path(args.file).read_text(encoding="utf-8") if args.file else sys.stdin.read()
    c = classify(args.url, text)
    print(c.model_dump_json(indent=2))
    for x in extract_contacts(text, args.url):
        print("contact:", {k: v for k, v in x.as_dict().items() if v and k != "extra"})
    for m in extract_mentions(text):
        print("mention:", m.signals, m.categories, m.sentence[:160])
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="mef", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    def filters(sp):
        sp.add_argument("--group", action="append", help="query group(s) from config/queries.yaml")
        sp.add_argument("--lang", action="append", help="language code(s)")
        sp.add_argument("--country", action="append", help="country key(s) from queries.yaml geography")
        sp.add_argument("--limit", type=int)

    sp = sub.add_parser("queries", help="print generated search queries"); filters(sp); sp.set_defaults(fn=cmd_queries)
    sp = sub.add_parser("search", help="run queries and store results"); filters(sp)
    sp.add_argument("--backend", choices=["ddgs", "searxng"]); sp.set_defaults(fn=cmd_search)
    sp = sub.add_parser("import-results", help="import search results (json/jsonl/csv)")
    sp.add_argument("file"); sp.set_defaults(fn=cmd_import_results)
    sp = sub.add_parser("collect", help="fetch + parse + classify top search results")
    sp.add_argument("--min-relevance", type=float, default=2.0)
    sp.add_argument("--limit", type=int, default=50)
    sp.add_argument("--llm", action="store_true", help="also assess candidates with Claude")
    sp.set_defaults(fn=cmd_collect)
    sp = sub.add_parser("triage", help="write draft museum files to research/inbox/")
    sp.add_argument("--min-relevance", type=float, default=3.0); sp.set_defaults(fn=cmd_triage)
    sp = sub.add_parser("fts", help="full-text search collected pages")
    sp.add_argument("query"); sp.add_argument("--limit", type=int, default=20); sp.set_defaults(fn=cmd_fts)
    sp = sub.add_parser("classify-text", help="classify a text file (or stdin)")
    sp.add_argument("--url", default="https://example.org/"); sp.add_argument("--file")
    sp.set_defaults(fn=cmd_classify_text)

    for name, fn, help_ in [
        ("validate", cmd_validate, "validate research/museums/*.yaml"),
        ("dedupe", cmd_dedupe, "report duplicate museums / evidence"),
        ("build", cmd_build, "rebuild SQLite database from research files"),
        ("export", cmd_export, "write CSV + XLSX exports"),
        ("stats", cmd_stats, "print research statistics"),
    ]:
        sub.add_parser(name, help=help_).set_defaults(fn=fn)
    sp = sub.add_parser("report", help="generate the research-run report")
    sp.add_argument("--label", default="run"); sp.set_defaults(fn=cmd_report)
    sp = sub.add_parser("all", help="validate → dedupe → build → export → report → stats")
    sp.add_argument("--label", default="run"); sp.set_defaults(fn=cmd_all)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
