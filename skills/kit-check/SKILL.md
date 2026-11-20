---
name: kit-check
description: Use when the user asks what to wear for a run (or ride/walk) at a given time and place, gives post-run kit feedback ("too warm", "hands froze"), or wants to add a clothing rule ("always gloves below 8°C").
---

# Kit Check

Recommend running kit from the hourly forecast and the session type. Personal rules and feedback-based tuning are kept in local JSON files.

## 0. Storage

The user's data lives in a folder called `kit-check/` that holds two files:
- `rules.json`: settings and user rules (the user may hand-edit it)
- `log.json`: post-run feedback entries (Claude appends to it)

Find the folder:
- **Claude Code**: `./kit-check/` in the current project if it exists (project-based), else `~/kit-check/` (home-based). Never store user data inside the skill or plugin folder, because updates overwrite it.
- **Chat linked to the desktop app**: look in the user's connected folders with the mcp__remote-devices__ tools.
- **Neither available** (e.g. plain claude.ai): carry on with the built-in defaults, and ask for a location if none was given. Tell the user once that rules and tuning need Claude Code or a connected folder to persist.

First run: if the folder doesn't exist but storage is available, offer to create it.
1. In Claude Code, ask where to keep it: **project** (`./kit-check/`, easy to back up and resume with the project) or **home** (`~/kit-check/`, shared by every project; the default). Create it there. If it's in a git repo, mention that the user may want to commit or ignore it, since it holds their location.
2. Ask how to set the home location (IP lookup is the default if the user just says yes):
   - **IP-based**: WebFetch `https://ipapi.co/json/` and use `city`, `country_name`, `latitude`, `longitude`. Show the result and let the user correct it. IP lookups can be off by a city or more, and wrong on a VPN.
   - **User specified**: `lat,lon` (use as given) or `town, country` (geocode it with the Open-Meteo geocoding API in section 1, using the resolved name, lat and lon, and show the match so the user can confirm it).
3. Ask how times are written: 24-hour (default, "0900", "18:30") or 12-hour ("9am", "6:30pm"). Store it in `settings.time_format` (`"24h"` or `"12h"`). Either way, an explicit am/pm in a message is always honoured; with `24h`, a bare number like "9" or "0900" is 24-hour, and with `12h` ask if a bare hour is ambiguous.
4. Ask where run plans live: Strava, Claude's memory, a local file or folder (get the path), or none. Store it in `settings.plan_source` as `{ "type": "strava|memory|file|none", "path": "" }`.
5. Copy `templates/rules.json` and `templates/log.json` from this skill's folder.
6. Store the location in `settings.default_location` as `name`, `lat`, `lon`. It is fixed from then on; never re-run IP discovery for later requests.

File handling:
- Re-read a file right before every write. Never rebuild it from an earlier or truncated read.
- Write valid, pretty-printed JSON (2-space indent).
- If a file fails to parse, don't overwrite it. Report the error and use the defaults.

## 1. Gather inputs

- **Location**: `settings.default_location` for every request. A place named in the message overrides it for that request only; never save it. If no default is set, ask. Geocode place names with WebFetch:
  `https://geocoding-api.open-meteo.com/v1/search?name=<PLACE>&count=1&language=en&format=json`
- **Plan**: read the next planned run from `settings.plan_source` and use its date, time, session and duration as defaults. Anything stated in the message overrides the plan field by field, for that request only. Say which plan entry you used. If `plan_source` is `none`, unset, unreadable, or has no upcoming run, fall through to the next rules.
  - `strava`: Strava's `get_training_plan`.
  - `memory`: look in Claude's memory for the plan itself, or for a note saying where it is (a file, folder or other source), then read it from there.
  - `file`: the file or folder at `plan_source.path`. For a folder, read every plan file in it and pick the next upcoming run across them. Interpret whatever layout (CSV, TXT, JSON, etc.) it has.
  - A plan named in the message or found in the current session's files (e.g. an attached CSV) beats `plan_source` for that request.
- **Time**: the date and hour the user names ("tomorrow at 0900"), parsed per `settings.time_format`. Else the plan's time, else the next whole hour. Use `settings.timezone` if set, else `auto`.
- **Session**: sort whatever the user says into one of three types. Use `settings.session_aliases` if present, else:
  - **easy**: easy, zone 2, z2, recovery, base, jog, shakeout, easy + strides
  - **long**: long, long run, LSR, or any easy-paced run over 75 min
  - **speed**: tempo, threshold, intervals, reps, track, fartlek, hills, progression, VO2, parkrun, race, or anything described as fast or hard
  - A long run with fast sections (tempo finish, marathon-pace blocks) is **long**, with +2°C added to its offset.
  - If unclear, use `settings.default_session`, else easy, and say so.
- **Duration**: from the message ("2 hour run"), else the plan, else assume 60 min and say so. If it's over 75 min, also check the forecast for the finish hour.

Don't ask questions when defaults will do; state the assumptions in one line.

## 2. Fetch the forecast

Use WebFetch (not curl):
```
https://api.open-meteo.com/v1/forecast?latitude=<LAT>&longitude=<LON>&hourly=temperature_2m,apparent_temperature,precipitation_probability,precipitation,wind_speed_10m,wind_gusts_10m,relative_humidity_2m,uv_index,is_day&wind_speed_unit=mph&timezone=<TZ or auto>&forecast_days=7
```
Ask the fetch prompt for the exact values at the target hour (and the finish hour).

Condition variables used by rules:
`temp_c`, `feels_like_c`, `t_run_c`, `wind_mph`, `gust_mph`, `precip_prob_pct`, `precip_mm`, `humidity_pct`, `uv`, `is_dark` (bool), `session` (easy/long/speed), `duration_min`, `month` (1-12)

If `settings.units.temp` is `"F"` or `settings.units.wind` is `"kmh"`, convert for display only. Rules and the log stay in °C and mph.

## 3. Run temperature

t_run_c = feels_like_c + session offset + `settings.personal_offset_c` + learned band offset (section 6)

Session offsets (taken from `settings.session_offsets_c` if present): easy +6, long +5, speed +9. Speed sessions generate the most heat, so they get the least kit.

## 4. Default kit

Base kit by t_run_c:

| t_run_c | top | bottom | extras |
|---|---|---|---|
| ≥ 22 | singlet | shorts | cap, sunscreen, water |
| 16–22 | t-shirt | shorts | — |
| 11–16 | t-shirt | shorts | arm sleeves (optional) |
| 6–11 | long sleeve | shorts | light gloves |
| 1–6 | long sleeve + gilet | tights | gloves, headband |
| −4–1 | thermal base + jacket | tights | gloves, beanie, buff |
| < −4 | 2 base layers + windproof | winter tights | mittens, beanie, buff |

Built-in modifiers:
- **Rain**: precip_prob_pct ≥ 50 or precip_mm ≥ 0.5 → waterproof shell and a peaked cap. 30–49 → just mention it.
- **Wind**: wind_mph ≥ 15 or gust_mph ≥ 25 → windproof layer, gloves. Suggest heading out into the wind and coming back with it.
- **Dark**: is_dark → hi-vis or reflective kit, head torch.
- **UV**: uv ≥ 3 → sunglasses and sunscreen; uv ≥ 6 → also a cap.
- **Warm and humid**: t_run_c ≥ 16 and humidity ≥ 80 → lightest kit, carry fluids.
- **Ice**: temp_c < 2 after rain → warn about ice.

Session guidance:
- **easy**: dress for steady effort at the start temperature. This is the baseline.
- **long**: dress for the middle of the run. Check the finish hour; if it differs by more than 3°C or rain starts, say so. Prefer layers that can come off and be carried (gilet, arm sleeves, light gloves). Mention fuel and fluids if t_run_c ≥ 16.
- **speed**: dress for the hard efforts, not the warm-up. If t_run_c < 10, add a throw-off layer (old long sleeve or gilet) for the warm-up, recoveries and cool-down. Keep gloves and a hat optional, since they're easy to take off. Shorts unless t_run_c < 2.

## 5. User rules (rules.json)

Apply user rules after the defaults, in file order. User rules beat the defaults.

```json
{
  "id": "gloves-below-8",
  "enabled": true,
  "when": { "feels_like_c": { "lt": 8 } },
  "add": ["gloves"],
  "remove": [],
  "set": { "bottom": "shorts" },
  "note": "Hands always get cold first"
}
```

- `when`: every condition must hold (AND).
  - Numeric operators: `lt`, `lte`, `gt`, `gte`, `eq`.
  - Lists: `in`, e.g. `"session": {"in": ["easy","long"]}`.
  - Booleans: `true`/`false`.
  - A missing `when` means the rule always applies.
- `add`: append items. `remove`: drop matching items. `set`: replace a slot (`top`, `bottom`, `head`, `hands`, `outer`, `extras`).
- `note`: shown with the recommendation when the rule fires.
- Skip rules with `enabled: false`.
- `settings.never`: items never to suggest, applied last.
- `settings.wardrobe` (optional): if non-empty, suggest only owned items, picking the nearest equivalent.

When the user states a standing rule ("always gloves below 8", "never 3/4 tights", "shorts for speed sessions unless it's freezing"):
1. Turn it into a rule.
2. Show it in one line.
3. Re-read rules.json, append the rule with a unique kebab-case `id` (or add the item to `never`), then write the file.

If an `id` already exists, update that rule instead of adding a duplicate.

If the user names a new session word ("call hill sprints speed"), add it to `settings.session_aliases` the same way.

## 6. Feedback log and tuning (log.json)

When the user reports how a run felt, re-read log.json and append an entry to `entries`:
```json
{
  "date": "2026-11-19T07:00",
  "location": "Home",
  "session": "easy",
  "session_detail": "zone 2",
  "duration_min": 45,
  "feels_like_c": 3.1,
  "wind_mph": 9,
  "precip_prob_pct": 20,
  "t_run_c": 9.1,
  "wore": ["long sleeve", "shorts", "gloves"],
  "rating": 1,
  "comment": "warm by 2k"
}
```
- `rating`: −2 way too cold, −1 a bit cold, 0 right, +1 a bit warm, +2 way too warm.
- `session_detail`: the user's own words for the session.
- Weather values: use the ones from this conversation if you have them. Otherwise fetch the hour from `https://archive-api.open-meteo.com/v1/archive` (same parameters plus `start_date`/`end_date`), or ask.
- If something specific was wrong ("hands froze"), also suggest a rule.

Learned band offset, worked out before each recommendation:
- Use entries from the last 120 days.
- Bucket them by feels_like_c into 5°C bands (…, 0–5, 5–10, …).
- If the target band has ≥ 3 entries **of the same session type**: band_offset = 1.5 × mean(rating), clamped to ±4°C.
- Else if the target band has ≥ 3 entries of any session type: use their mean, clamped to ±3°C.
- Else if there are ≥ 5 entries overall: use 1.5 × overall mean, clamped to ±2°C.
- Else: 0.

A positive rating means the user ran warm, so t_run_c goes up and they get less kit. Speed sessions tune separately because they run hotter.

If the offset isn't zero, mention it briefly, e.g. "tuned +1.5°C from your last 4 easy runs at this temp".

## 7. Reply format (short, phone-friendly)

1. One line: place, time, session type, conditions (temp/feels-like, wind, rain chance), and any tuning applied.
2. Kit: top, bottom, head, hands, outer, extras (skip empty slots).
3. Notes from any rules that fired, plus at most one tip.
4. Optionally: "Tell me how it felt afterwards and I'll log it."
