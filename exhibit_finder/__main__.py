"""Command line interface.

  python -m exhibit_finder check  CANDIDATES.json [--out DIR] [--include-weak]
  python -m exhibit_finder queries [--groups A B] [--per-concept N] [--csv FILE]
"""

import argparse
import csv
import json
import os
import sys

from . import database, queries


def cmd_check(args):
    cands = database.load_candidates(args.candidates)
    db, rejected = database.build(cands, include_weak=args.include_weak)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "database.json"), "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "rejected.json"), "w", encoding="utf-8") as f:
        json.dump(rejected, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "database.md"), "w", encoding="utf-8") as f:
        f.write(database.to_markdown(db, rejected))
    for r in db:
        print(f"{r['ACQUISITION_PRIORITY']:6} {r['MUSEUM_RELEVANCE']:13} {'IDEAL ' if r['IDEAL_TARGET'] else '      '}"
              f"{r['old_exhibit']} -- {r['museum']}")
    for r in rejected:
        print(f"{'-':6} {r['MUSEUM_RELEVANCE']:13}       {r['old_exhibit']} -- DO NOT RECOMMEND")
    print(f"\n{len(db)} kept, {len(rejected)} rejected. Written to {args.out}/", file=sys.stderr)


def cmd_queries(args):
    rows = list(queries.generate(groups=tuple(args.groups), per_concept=args.per_concept,
                                 negatives=not args.no_negatives))
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["category", "concept", "query"])
            w.writeheader()
            w.writerows(rows)
        print(f"{len(rows)} queries written to {args.csv}", file=sys.stderr)
    else:
        for r in rows:
            print(r["query"])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="exhibit_finder")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="run the relevance check and build the acquisition database")
    c.add_argument("candidates")
    c.add_argument("--out", default="out")
    c.add_argument("--include-weak", action="store_true", help="keep WEAK_MATCH objects in the database")
    c.set_defaults(func=cmd_check)

    q = sub.add_parser("queries", help="generate targeted search queries from the museum profile")
    q.add_argument("--groups", nargs="+", default=["A"], choices=["A", "B"])
    q.add_argument("--per-concept", type=int, default=3)
    q.add_argument("--no-negatives", action="store_true")
    q.add_argument("--csv")
    q.set_defaults(func=cmd_queries)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
