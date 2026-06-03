# AGENTS.md — Key findings & institutional knowledge

This file documents important findings, bugs, and architectural decisions for
future agents (or humans) working on this repo.

---

## What this project does

Scrapes [frankdeboosere.be](https://www.frankdeboosere.be) daily for the "Meer
Weer" weather podcast MP3, stores episodes in a SQLite database (`episodes.db`),
and generates an RSS feed (`podcast.xml`). A GitHub Actions workflow
(`.github/workflows/daily.yml`) runs the scraper every day at 06:00 UTC.

---

## Bug: recycled MP3 filenames cause silent daily collisions (FIXED)

### Root cause
The website reuses the same MP3 filename for the same calendar day every year:

```
/podcast/juni/03jun_wAar_alg.mp3   ← used every 3 June, regardless of year
```

The `episodes` table has `url TEXT UNIQUE`. The DB was backfilled with one row
per calendar day (365 rows total). So every new daily episode collided on the
`UNIQUE url` constraint with last year's row for that day, was silently skipped,
and `episodes.db` / `podcast.xml` were never updated. The feed was stuck at
**30 July 2025** for ~10 months while the workflow appeared to run fine.

### Fix (commit `aed6e53`)
`add_episode()` now accepts a `replace_existing=False` keyword argument.

- The **daily** episode call passes `replace_existing=True`: on
  `IntegrityError` it `DELETE`s the stale prior-year row and re-inserts the
  current one. Total row count stays at 365 (rolling, one per calendar day).
- The **special/extra podcast** loop leaves `replace_existing=False` (skip on
  duplicate) — those have unique date-stamped filenames
  (e.g. `frankdeboosere20191214.mp3`) and must not be overwritten.

### Key numbers
- DB always has ~365 rows (one per calendar day, rolling yearly).
- 11 special/extra podcast rows have unique URLs — never affected by collisions.

---

## Bug: `[skip ci]` in commit message disabled the scheduled workflow (FIXED)

### Root cause
The automated commit used `git commit -m "Podcast feed update [skip ci]"`.
GitHub interprets `[skip ci]` as an instruction to skip **all** CI for that
push, which eventually caused GitHub to auto-disable the entire scheduled
workflow after 60 days of inactivity.

### Fix (commit `e3d7f0d`)
Removed `[skip ci]` from the commit message in `.github/workflows/daily.yml`.
The workflow now commits with `"Podcast feed update"` — no suppression.

---

## MP3 URL resolution logic

The scraper tries two sources in order:

1. **Dynamic URL**: `/alert/Alert.mp3?cachekill=<timestamp>` — a cache-busting
   link that sometimes returns HTTP 200 but in practice usually 404.
2. **Fallback URL**: extracted from `var fallback = "..."` in the page HTML
   (e.g. `/podcast/juni/03jun_wAar_alg.mp3`). This is almost always the one
   that actually works.

If neither returns 200, no episode is added for that day and a warning is
printed.

---

## Known remaining issue: RSS feed ordering is broken

`generate_rss()` sorts episodes with `ORDER BY pub_date DESC`, but `pub_date`
is stored as an RFC-822 string (`"Wed, 03 Jun 2026 07:23:41 GMT"`). SQLite sorts
it **lexicographically** (by weekday name), not chronologically. The newest
episode is therefore not reliably at the top of `podcast.xml`.

**Fix**: either store a separate ISO date column for sorting, or parse the
RFC-822 string into a `datetime` in Python before sorting.

---

## GitHub Actions workflow (`.github/workflows/daily.yml`)

| Item | Value |
|---|---|
| Schedule | `0 6 * * *` (06:00 UTC daily) |
| Trigger | `schedule` + `workflow_dispatch` |
| `actions/checkout` | `@v6` (bumped from v3 → v4 → v6 in this session) |
| `actions/setup-python` | `@v6` (bumped from v4 → v5 → v6 in this session) |

**Always check for latest action versions before assuming they are current.**
Both `checkout` and `setup-python` jumped to v6 while the workflow was still
on v3/v4 (Node 16 — deprecated by GitHub as of June 2026).

---

## File map

| File | Purpose |
|---|---|
| `script.py` | Main scraper + DB writer + RSS generator |
| `episodes.db` | SQLite database of all episodes |
| `podcast.xml` | Generated RSS feed (committed to repo) |
| `requirements.txt` | Python dependencies (`requests`, `beautifulsoup4`) |
| `.github/workflows/daily.yml` | Scheduled CI workflow |
| `backfill.py` | One-off historical backfill script (not part of daily run) |
| `archive.py`, `check.py` | Scratch/utility scripts (not part of daily run) |
