# Whiffs: MLB Projection Accuracy Evaluation

**Whiffs** is a comprehensive evaluation of MLB projection system accuracy, comparing Marcel, Steamer, and ZiPS projections against actual player performance from 2010-2024.

The analysis follows Tom Tango's methodology for evaluating projection systems, adjusting for league averages and weighting errors by playing time to provide meaningful accuracy metrics.

## 🔗 Live Site

Visit [Whiffs.org](https://whiffs.org) to explore the interactive charts and analysis.

## 📊 Methodology

Whiffs implements three key principles from Tom Tango's posts on projection evaluations:

### 1. Separate Playing Time from Rate Stats
- Playing time (PA/BF) is evaluated independently from rate statistics
- Prevents misleading assessments where playing time and rate errors cancel out
- Rate stats are normalized per plate appearance (PA) or batters faced (BF)

### 2. Adjust for League Average
- Errors are calculated after adjusting for projected vs actual league averages
- Ensures projections are evaluated on their ability to predict player performance relative to league context
- A player performing at league average should be projected as league average, regardless of raw numbers

### 3. Weight by Playing Time
- Errors are weighted by actual playing time (PA/BF) to reflect real-world impact
- A projection error for a 600 PA player matters more than the same error for a 100 PA player
- Prevents systems from being equally penalized for mistakes on marginal vs regular players

See more at [Whiffs Methodology](https://whiffs.org/methodology).

## 🏗️ Build Process

**Whiffs** evaluations are built in Python. The resulting data is built into a static site using Eleventy.

### Prerequisites

**Python**: Install Python from [python.org](https://www.python.org/downloads/) or your package manager.

**uv**: [Install uv](https://docs.astral.sh/uv/getting-started/installation/) if you haven't already and then collect dependencies with:
```bash
uv sync
```

**Node.js**: Install [Node.js](https://nodejs.org/) and then Eleventy dependencies:
```bash
npm install
```

### Collect projections

Projections and stats are not included in the repository, so you'll need to build or find those first.

1. **Fetch MLB Stats Data**

   ```bash
   python fetch_mlb_stats.py
   ```
   First, you need the actual player stats. This will download actual player statistics from MLB's Stats API for 2007-2024 into the `/stats` directory. These are needed for building the Marcel projections and for assessing projection accuracy.

   This will also collect some biographical data, as birthdates are needed for building Marcels.

2. **Build Marcels**

    ```bash
    python marcel-like.py
    ```

    Builds Marcel-like projections into `/projections` using the MLB data from Step 1.

    *Note: these differ somewhat from the [official Marcel projections](https://www.tangotiger.net/marcel/). If you can improve my code, please go for it!*

3. **Add historical Steamer and ZiPS from FanGraphs**

    [Historical Steamer and ZiPS projections](https://www.fangraphs.com/projections) are available on FanGraphs for members.

    Whiffs expects these to be in the `/projections` directory in a format like `steamer_2012_bat.csv`.

### Run the evaluation

  Once you've got all your stats and projection data in place, you can run the projection evaluation:

  ```bash
  python projection_evaluation.py
  ```
  This will build some JSON files into `/src/_data` that will be processed by Eleventy in the next step.

### Generate the website

If you've got Node and Eleventy installed and built the JSON data files, you can now run Eleventy to build the site:

   ```bash
   npx @11ty/eleventy --serve
   ```


## 📜 License

This project is licensed under the **MIT License**.

See the [LICENSE](LICENSE) file for full details.

## 🤝 More projections

I'm hoping to add more historical projections to the comparison set. If you've saved some, or if you are the creator of a projection system, contact me and I'll be happy to add them to the analysis.