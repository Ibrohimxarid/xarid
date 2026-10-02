"""Small helper to patch research YAML files (used for bulk annotation).

    from yaml_patch import load, save, exhibit, exhibition
"""
from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent / "research" / "museums"


class _Dumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):  # indent list items under keys
        return super().increase_indent(flow, False)


def _list(dumper, data):
    flow = all(not isinstance(x, (dict, list)) for x in data)
    return dumper.represent_sequence("tag:yaml.org,2002:seq", data, flow_style=flow)


def _dict(dumper, data):
    return dumper.represent_mapping("tag:yaml.org,2002:map", data.items(), flow_style=False)


def _str(dumper, data):
    style = '"' if any(data.startswith(p) for p in ("http",)) is False and _needs_quotes(data) else None
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=style)


def _needs_quotes(s: str) -> bool:
    import re
    return bool(re.fullmatch(r"\d{4}([-–]\d{2}([-–]\d{2})?)?|\d{4}[-–]\d{4}", s))


_Dumper.add_representer(list, _list)
_Dumper.add_representer(dict, _dict)
_Dumper.add_representer(str, _str)


def load(mid: str) -> dict:
    return yaml.safe_load((ROOT / f"{mid}.yaml").read_text(encoding="utf-8"))


def save(mid: str, data: dict) -> None:
    text = yaml.dump(data, Dumper=_Dumper, sort_keys=False, allow_unicode=True, width=1000)
    (ROOT / f"{mid}.yaml").write_text(text, encoding="utf-8")


def exhibition(data: dict, ex_id: str) -> dict:
    return next(e for e in data["exhibitions"] if e["id"] == ex_id)


def exhibit(data: dict, item_id: str) -> dict:
    return next(i for e in data["exhibitions"] for i in e.get("exhibits", []) if i["id"] == item_id)
