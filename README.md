# Whiffs, Bricks, and Drops

This repository holds three peer projection-evaluation pipelines:

- **Whiffs** ([whiffs.org](https://whiffs.org)) — MLB projection accuracy (Marcel, Steamer, ZiPS, and others)
- **Bricks** — NBA projection accuracy (SPS, ESPN, and DARKO)
- **Drops** — NFL projection accuracy

Baseball code and data live under [`baseball/`](baseball/). Basketball code and data live under [`basketball/`](basketball/). Football code and data live under [`football/`](football/). Root scripts always name the sport.

## Prerequisites

**Python**: Install Python from [python.org](https://www.python.org/downloads/) or your package manager.

**uv**: [Install uv](https://docs.astral.sh/uv/getting-started/installation/) if you haven't already, then:

```bash
uv sync
```

**Node.js**: Install [Node.js](https://nodejs.org/) for the Tailwind CLI, then:

```bash
npm install
```

## Baseball (Whiffs)

Whiffs compares Marcel, Steamer, ZiPS, and other MLB projection systems against actual player performance from 2010–2024, following Tom Tango's methodology: separate playing time from rate stats, adjust for league average, and weight errors by playing time.

See [Whiffs Methodology](https://whiffs.org/methodology).

### Collect projections

Projections and stats are not included in the repository.

1. **Fetch MLB Stats Data**

   ```bash
   npm run baseball:stats
   ```

   Downloads actual player statistics from MLB's Stats API for 2007–2024 into `baseball/stats/`, plus biographical data needed for Marcels.

2. **Build Marcels**

   ```bash
   npm run baseball:marcel
   ```

   Builds Marcel-like projections into `baseball/projections/`.

   *These differ somewhat from the [official Marcel projections](https://www.tangotiger.net/marcel/). Improvements welcome.*

3. **Add historical Steamer and ZiPS from FanGraphs**

   [Historical Steamer and ZiPS projections](https://www.fangraphs.com/projections) are available on FanGraphs for members. Place them in `baseball/projections/` in a format like `steamer_2012_bat.csv`.

### Build the site

```bash
npm run baseball
```

That runs evaluation, HTML rendering, and CSS in sequence. Individual steps:

```bash
# Projection evaluation + write baseball/reports/site_cache/ (no HTML)
npm run baseball:evals

# Re-render HTML from cache into baseball/_site/ (requires a prior evals)
npm run baseball:site

# Compile Tailwind CSS into baseball/_site/assets/css/style.css
npm run baseball:css
```

Use `npm run baseball` (or at least `baseball:evals`) when projection/stats data changes. For template iteration, `npm run baseball:site` (and `baseball:css` if you added new Tailwind classes). For theme-only tweaks to `input.css`, `baseball:css` alone is enough.

### Local preview

```bash
npm run baseball:serve
```

Then open http://localhost:8080

### Deploy

Build first (`npm run baseball`), then upload to the Whiffs Cloudflare Pages project:

```bash
npm run baseball:deploy
```

## Basketball (Bricks)

Bricks is the NBA counterpart to Whiffs: Tango-style projection evaluation with minutes-weighted, league-adjusted rate errors. Season files use NBA calendar-overlap labels (`basketball/stats/2023-24.csv`). SPS writes `basketball/projections/sps_2009-10.csv` through `sps_2026-27.csv`.

### Collect stats and build SPS

```bash
# Regular-season player totals + bios into basketball/stats/
npm run basketball:stats

# Basketball-Reference Simple Projection System into basketball/projections/
npm run basketball:sps

# ESPN fantasy season projections (2017-18 through 2026-27)
npm run basketball:espn

# Historical DARKO box-score projections (2006-07 through 2025-26)
npm run basketball:darko
```

### Build the site

```bash
npm run basketball
```

Individual steps:

```bash
npm run basketball:evals   # evaluation + basketball/reports/site_cache/
npm run basketball:site    # HTML into basketball/_site/
npm run basketball:css     # Tailwind CSS
npm run basketball:serve   # http://localhost:8081
```

### Deploy

Build first (`npm run basketball`), then upload to the Bricks Cloudflare Pages project:

```bash
npm run basketball:deploy
```

Create the `bricks` Pages project once (`npx wrangler pages project create bricks`) before the first deploy.

## Football (Drops)

Drops is the NFL counterpart to Whiffs. Playing time stays separate from rate stats: pass attempts, carries, and targets are the weights, and accuracy, yards, touchdowns, interceptions, and catch rate are scored as rates. Actuals are scraped from the NFL.com passing, rushing, and receiving leaderboards and stored under each player's `nfl_slug`.

Season files are named with the NFL season year (`football/stats/2024.csv`).

### Collect stats

```bash
# Every season the current NFL.com leaderboards still serve
npm run football:stats

# One season
npm run football:stats -- --season 2024
```

ESPN, Sleeper, FFToday, and FantasyPros season-long projections use `football/projections/{prefix}_{season}.csv` (for example `espn_2024.csv` for ESPN). Download them with `npm run football:espn`, `npm run football:sleeper`, `npm run football:fftoday`, and `npm run football:fantasypros`. ESPN 2023 is left out: that season's projection split is empty for most players. FantasyPros reads the session cookie from `FANTASYPROS_COOKIE` and does not store it in the script; without that cookie the live draft board is only a short public list. Seasons 2018–2022 are filled from Wayback Machine captures of the preseason draft board, because the live `year=` pages omit players who have since left the league. A position with no preseason capture keeps the players already in the saved file. Scored systems are listed in `PROJECTION_SYSTEMS` inside `football/projection_evaluation.py`; add a display name there and map it to the file prefix in `PROJECTION_SYSTEM_FILES` when they differ. Joins use `nfl_slug` from [`player_ids.csv`](https://github.com/mayscopeland/ffb_ids) in [mayscopeland/ffb_ids](https://github.com/mayscopeland/ffb_ids). The fetchers download that file. When an older id is missing and the player name matches one slug, that slug is used for the projection row. The crosswalk on GitHub is left unchanged. FantasyPros does not publish targets, so that file omits `TGT` the same way FFToday does.

Fantasy pages use the top 150 offensive players by FantasyPros half-PPR preseason ADP. Download that board with `npm run football:adp`. It reads the same `FANTASYPROS_COOKIE` and writes `football/adp/fantasypros_{season}.csv` with kickers and defenses already removed.

### Build the site

```bash
npm run football
```

Individual steps:

```bash
npm run football:evals   # evaluation + football/reports/site_cache/
npm run football:site    # HTML into football/_site/
npm run football:css     # Tailwind CSS
npm run football:serve   # http://localhost:8082
```

### Deploy

Build first (`npm run football`), then upload to the Drops Cloudflare Pages project:

```bash
npm run football:deploy
```

Create the `drops` Pages project once (`npx wrangler pages project create drops`) before the first deploy.

## License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for full details.

## More projections

I'm hoping to add more historical projections to the comparison set. If you've saved some, or if you are the creator of a projection system, contact me and I'll be happy to add them to the analysis.
