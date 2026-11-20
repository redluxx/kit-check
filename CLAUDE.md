# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Claude Code plugin/skill with no code, build, lint or test tooling. The whole product is prompt text in `skills/kit-check/SKILL.md` plus two JSON templates. "Developing" means editing those files.

## Layout

- `.claude-plugin/plugin.json` and `marketplace.json`: plugin metadata (keep the version and repo URLs in sync).
- `skills/kit-check/SKILL.md`: the skill. Sections are numbered: 0 storage, 1 inputs, 2 forecast (Open-Meteo via WebFetch), 3 run temperature, 4 default kit, 5 user rules, 6 feedback log and tuning.
- `skills/kit-check/templates/rules.json` and `log.json`: copied to the user's `~/kit-check/` on first run.

## Things to keep consistent

- The rule schema (conditions, operators, actions, slots) and the session types, offsets and aliases are described in both `SKILL.md` and `README.md`, and defaults also live in `templates/rules.json`. Change all of them together.
- User data must never be stored inside the skill or plugin folder, because plugin updates overwrite it.
- Rules and the log stay in °C and mph. Unit conversion is for display only.
- Skill instructions tell Claude to use WebFetch, not curl, for Open-Meteo calls.
