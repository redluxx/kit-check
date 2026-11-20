#!/usr/bin/env python3
"""Validate everything the plugin ships to a client. Stdlib only; exit 1 on any error."""
import json, re, sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
errors = []

def err(msg): errors.append(msg)

def load(rel):
    try:
        return json.loads((root / rel).read_text())
    except (OSError, ValueError) as e:
        err(f"{rel}: {e}")

plugin = load(".claude-plugin/plugin.json") or {}
market = load(".claude-plugin/marketplace.json") or {}
rules = load("skills/kit-check/templates/rules.json") or {}
log = load("skills/kit-check/templates/log.json") or {}

# versions and repo metadata stay in sync
v = plugin.get("version")
if not re.fullmatch(r"\d+\.\d+\.\d+", str(v)): err(f"plugin.json: bad version {v!r}")
mv = [market.get("metadata", {}).get("version")] + [p.get("version") for p in market.get("plugins", [])]
if any(x != v for x in mv): err(f"marketplace.json versions {mv} != plugin.json {v}")
for p in market.get("plugins", []):
    if p.get("name") != plugin.get("name"): err(f"marketplace plugin name {p.get('name')!r} != {plugin.get('name')!r}")
    if not (root / p.get("source", "")).is_dir(): err(f"marketplace source {p.get('source')!r} is not a directory")
for k in ("name", "description", "repository"):
    if not plugin.get(k): err(f"plugin.json: missing {k}")

# SKILL.md frontmatter: name must match its folder
skill = root / "skills/kit-check/SKILL.md"
m = re.match(r"---\n(.*?)\n---\n", skill.read_text(), re.S)
fm = dict(l.split(":", 1) for l in m.group(1).splitlines() if ":" in l) if m else {}
if not m: err("SKILL.md: no frontmatter")
elif fm.get("name", "").strip() != skill.parent.name or not fm.get("description", "").strip():
    err("SKILL.md: frontmatter needs name (= folder name) and description")

# templates: schema the skill documents (SKILL.md section 5)
for name, doc in (("rules.json", rules), ("log.json", log)):
    if doc.get("version") != 1: err(f"{name}: version must be 1")
if not isinstance(log.get("entries"), list): err("log.json: entries must be a list")

OPS = {"lt", "lte", "gt", "gte", "eq", "in"}
SLOTS = {"top", "bottom", "head", "hands", "outer", "extras"}
ids = set()
for r in rules.get("rules", []):
    rid = r.get("id")
    if not rid or rid in ids: err(f"rules.json: missing or duplicate id {rid!r}")
    ids.add(rid)
    if not isinstance(r.get("enabled"), bool): err(f"rules.json[{rid}]: enabled must be boolean")
    for cond, test in r.get("when", {}).items():
        if not isinstance(test, (bool, dict)) or (isinstance(test, dict) and not set(test) <= OPS):
            err(f"rules.json[{rid}]: bad condition {cond}={test!r}")
    if not set(r.get("set", {})) <= SLOTS: err(f"rules.json[{rid}]: unknown slot in set")
    if not any(k in r for k in ("add", "remove", "set")): err(f"rules.json[{rid}]: no action")

s = rules.get("settings", {})
if set(s.get("session_offsets_c", {})) != set(s.get("session_aliases", {})):
    err("rules.json: session_offsets_c and session_aliases must have the same session types")
if s.get("default_session") not in s.get("session_aliases", {}): err("rules.json: default_session is not a session type")

print("\n".join(errors) or "ok")
sys.exit(bool(errors))
