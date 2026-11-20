# Kit Check

A Claude skill that tells you what to wear for a run. It uses:
- the hourly forecast (from [Open-Meteo](https://open-meteo.com), which is free and needs no API key)
- the session type: **easy**, **long** or **speed**
- your own rules ("always gloves below 8°C", "never 3/4 tights")
- feedback after each run ("too warm"), which tunes future suggestions

> "What should I wear for a zone 2 run at 7am?"
> "Tempo session at 6pm in Cheltenham, 50 minutes"
> "That was too warm, hands were fine"
> "Always wear a buff below 3°C"

## Install

### Claude Code (recommended: rules and tuning persist)

```
/plugin marketplace add YOUR-GITHUB-USERNAME/kit-check
/plugin install kit-check@kit-check
```

To update later, run `/plugin marketplace update`.

Or install manually: copy `skills/kit-check/` to `~/.claude/skills/kit-check/`.

### Claude.ai / Claude desktop app

1. Download `kit-check.zip` from the [latest release](https://github.com/YOUR-GITHUB-USERNAME/kit-check/releases/latest).
2. Go to **Settings → Capabilities → Skills → Upload skill** and pick the zip.

This needs a paid plan with code execution enabled. Rules and tuning only persist if the chat is linked to a folder on your computer through the desktop app. Otherwise the skill uses its built-in defaults.

## Your data

On first use, Claude offers to create the folder and asks for your default location:

Claude asks whether to keep it in the current project (`./kit-check/`, easy to back up and resume) or your home folder (`~/kit-check/`, the default). A project folder takes priority when present.

```
kit-check/
├─ rules.json   # settings and rules: edit freely
└─ log.json     # post-run feedback: Claude appends to it
```

Your data lives outside the skill folder, so updating the skill never touches it.

### Session types

| Session | Matches | Offset |
|---|---|---|
| easy | easy, zone 2, recovery, base, shakeout | +6°C |
| long | long, LSR, easy runs over 75 min | +5°C |
| speed | tempo, threshold, intervals, hills, parkrun, race | +9°C |

The skill adds the offset to the feels-like temperature and picks kit for the result. A bigger offset means less kit. You can add your own words for each type in `settings.session_aliases`.

### Rules

```json
{
  "id": "gloves-below-8",
  "enabled": true,
  "when": { "feels_like_c": { "lt": 8 } },
  "add": ["gloves"],
  "note": "Hands always get cold first"
}
```

- **Conditions** (all must match): `temp_c`, `feels_like_c`, `t_run_c`, `wind_mph`, `gust_mph`, `precip_prob_pct`, `precip_mm`, `humidity_pct`, `uv`, `is_dark`, `session`, `duration_min`, `month`
- **Operators**: `lt`, `lte`, `gt`, `gte`, `eq`, `in`
- **Actions**: `add`, `remove`, `set` (on the slots `top`, `bottom`, `head`, `hands`, `outer`, `extras`), `note`
- **Global settings**: `settings.never` lists items never to suggest; `settings.wardrobe` (optional) limits suggestions to kit you own.

### Tuning

After a run, tell Claude how it felt. It logs a rating from −2 (way too cold) to +2 (way too warm). Once there are 3 or more runs of the same session type at a similar feels-like temperature, it shifts the recommendation by about 1.5°C per rating point, up to ±4°C.

## Licence

MIT
