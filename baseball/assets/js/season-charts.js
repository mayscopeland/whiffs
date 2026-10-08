const DEFAULT_SEASON_BATTING_STATS = [
  { name: "wOBA", stat: "wOBA", isVolume: false },
  { name: "Strikeout Rate", stat: "SO/PA", isVolume: false },
  { name: "Walk Rate", stat: "BB/PA", isVolume: false },
  { name: "Hit By Pitch Rate", stat: "HBP/PA", isVolume: false },
  { name: "Home Run Rate", stat: "HR/BIP", isVolume: false },
  { name: "BABIP", stat: "BABIP", isVolume: false },
  { name: "Single Rate", stat: "1B/(BIP-HR)", isVolume: false },
  { name: "Double Rate", stat: "2B/(BIP-HR)", isVolume: false },
  { name: "Triple Rate", stat: "3B/(BIP-HR)", isVolume: false },
  { name: "Run Rate", stat: "R/PA", isVolume: false },
  { name: "RBI Rate", stat: "RBI/PA", isVolume: false },
  { name: "Stolen Base Rate", stat: "SB/TOF", isVolume: false },
  { name: "Batting Average", stat: "AVG", isVolume: false },
  { name: "On-Base Percentage", stat: "OBP", isVolume: false },
  { name: "Slugging Percentage", stat: "SLG", isVolume: false },
];

const DEFAULT_SEASON_PITCHING_STATS = [
  { name: "wOBA", stat: "wOBA", isVolume: false },
  { name: "Strikeout Rate", stat: "SO/BF", isVolume: false },
  { name: "Walk Rate", stat: "BB/BF", isVolume: false },
  { name: "Hit By Pitch Rate", stat: "HBP/BF", isVolume: false },
  { name: "Home Run Rate", stat: "HR/BIP", isVolume: false },
  { name: "BABIP", stat: "BABIP", isVolume: false },
  { name: "Single Rate", stat: "1B/(BIP-HR)", isVolume: false },
  { name: "Double Rate", stat: "2B/(BIP-HR)", isVolume: false },
  { name: "Triple Rate", stat: "3B/(BIP-HR)", isVolume: false },
  { name: "Run Rate", stat: "R/BF", isVolume: false },
  { name: "Earned Run Rate", stat: "ER/BF", isVolume: false },
  { name: "Win Rate", stat: "W/G", isVolume: false },
  { name: "Loss Rate", stat: "L/G", isVolume: false },
  { name: "Save Rate", stat: "SV/G", isVolume: false },
  { name: "Hold Rate", stat: "HLD/G", isVolume: false },
  { name: "ERA", stat: "ERA", isVolume: false },
  { name: "WHIP", stat: "WHIP", isVolume: false },
];

const FANTASY_SEASON_BATTING_STATS = [
  { name: "Home Run Rate", stat: "fan_HR/BIP", isVolume: false },
  { name: "Stolen Base Rate", stat: "fan_SB/TOF", isVolume: false },
  { name: "Run Rate", stat: "fan_R/PA", isVolume: false },
  { name: "RBI Rate", stat: "fan_RBI/PA", isVolume: false },
  { name: "Batting Average", stat: "fan_AVG", isVolume: false },
];

const FANTASY_SEASON_PITCHING_STATS = [
  { name: "Strikeout Rate", stat: "fan_SO/BF", isVolume: false },
  { name: "Win Rate", stat: "fan_W/G", isVolume: false },
  { name: "Save Rate", stat: "fan_SV/G", isVolume: false },
  { name: "ERA", stat: "fan_ERA", isVolume: false },
  { name: "WHIP", stat: "fan_WHIP", isVolume: false },
];

function initializeSeasonCharts(yearData, projectionSystems, options = {}) {
  if (!yearData) {
    console.error("No data provided for this year.");
    return;
  }

  const battingStats = options.battingStats || DEFAULT_SEASON_BATTING_STATS;
  const pitchingStats = options.pitchingStats || DEFAULT_SEASON_PITCHING_STATS;
  const battingVolumeStat = options.battingVolumeStat || "PA";
  const pitchingVolumeStat = options.pitchingVolumeStat || "BF";
  const battingVolumeLabel = options.battingVolumeLabel || "Batting PA";
  const pitchingVolumeLabel = options.pitchingVolumeLabel || "Pitching BF";

  // Helper function to clean stat names for chart IDs
  function cleanStatName(stat) {
    return stat.replace(/[\/\(\)\-]/g, "");
  }

  // Helper function to prepare stat-specific data
  function prepareStatSpecificData(yearData, playerType, stat, dataType, adjustment = null) {
    const results = yearData[playerType] || [];
    const statData = results.filter((result) => result.stat === stat);

    if (statData.length === 0) return null;

    const datasets = projectionSystems
      .map((system) => {
        const systemData = statData.find((result) => result.system === system);
        let value = null;

        if (systemData) {
          if (adjustment === "league-adj") {
            value = dataType === "MAE" ? systemData.la_mae : systemData.la_rmse;
          } else if (adjustment === "weighted-league-adj") {
            value = dataType === "MAE" ? systemData.wla_mae : systemData.wla_rmse;
          } else {
            value = dataType === "MAE" ? systemData.mae : systemData.rmse;
          }
        }

        return {
          label: system,
          data: [value],
          backgroundColor: projectionSystemColors[system] || defaultColor,
          borderColor: projectionSystemBorderColors[system] || defaultColor,
          borderWidth: 1,
          hasData: value !== null,
          errorValue: value, // Store the error value for sorting
        };
      })
      .filter((dataset) => dataset.hasData)
      .sort((a, b) => {
        // Sort by error value in descending order (worst to best)
        // Handle null values by putting them at the end
        if (a.errorValue === null && b.errorValue === null) return 0;
        if (a.errorValue === null) return 1;
        if (b.errorValue === null) return -1;
        return b.errorValue - a.errorValue;
      });

    // Remove the hasData and errorValue properties before returning
    datasets.forEach((dataset) => {
      delete dataset.hasData;
      delete dataset.errorValue;
    });

    return {
      labels: [stat],
      datasets: datasets,
    };
  }

  // Batting Charts
  if (yearData.batting && yearData.batting.length > 0) {
    // Volume MAE/RMSE
    const battingVolumeMaeData = prepareVolumeMaeData(yearData, "batting", projectionSystems, battingVolumeStat);
    createChart("battingVolumeMaeChart", "bar", battingVolumeMaeData, `${battingVolumeLabel} MAE`, "MAE");
    const battingVolumeRmseData = prepareVolumeRmseData(yearData, "batting", projectionSystems, battingVolumeStat);
    createChart("battingVolumeRmseChart", "bar", battingVolumeRmseData, `${battingVolumeLabel} RMSE`, "RMSE");

    // Individual batting stat charts
    battingStats.forEach((statInfo) => {
      const cleanName = cleanStatName(statInfo.stat);

      // Raw MAE/RMSE
      const maeData = prepareStatSpecificData(yearData, "batting", statInfo.stat, "MAE");
      if (maeData) {
        createChart(`batting${cleanName}MaeChart`, "bar", maeData, `${statInfo.name} (${statInfo.stat}) Raw MAE`, "MAE");
      }

      const rmseData = prepareStatSpecificData(yearData, "batting", statInfo.stat, "RMSE");
      if (rmseData) {
        createChart(`batting${cleanName}RmseChart`, "bar", rmseData, `${statInfo.name} (${statInfo.stat}) Raw RMSE`, "RMSE");
      }

      // League-Adjusted MAE/RMSE
      const leagueAdjMaeData = prepareStatSpecificData(yearData, "batting", statInfo.stat, "MAE", "league-adj");
      if (leagueAdjMaeData) {
        createChart(`batting${cleanName}LeagueAdjMaeChart`, "bar", leagueAdjMaeData, `${statInfo.name} (${statInfo.stat}) League-Adjusted MAE`, "League-Adjusted MAE");
      }

      const leagueAdjRmseData = prepareStatSpecificData(yearData, "batting", statInfo.stat, "RMSE", "league-adj");
      if (leagueAdjRmseData) {
        createChart(`batting${cleanName}LeagueAdjRmseChart`, "bar", leagueAdjRmseData, `${statInfo.name} (${statInfo.stat}) League-Adjusted RMSE`, "League-Adjusted RMSE");
      }

      // Weighted League-Adjusted MAE/RMSE
      const wlaMaeData = prepareStatSpecificData(yearData, "batting", statInfo.stat, "MAE", "weighted-league-adj");
      if (wlaMaeData) {
        createChart(`batting${cleanName}WLAMaeChart`, "bar", wlaMaeData, `${statInfo.name} (${statInfo.stat}) Weighted LA MAE`, "Weighted LA MAE");
      }

      const wlaRmseData = prepareStatSpecificData(yearData, "batting", statInfo.stat, "RMSE", "weighted-league-adj");
      if (wlaRmseData) {
        createChart(`batting${cleanName}WLARmseChart`, "bar", wlaRmseData, `${statInfo.name} (${statInfo.stat}) Weighted LA RMSE`, "Weighted LA RMSE");
      }
    });
  }

  // Pitching Charts
  if (yearData.pitching && yearData.pitching.length > 0) {
    // Volume MAE/RMSE
    const pitchingVolumeMaeData = prepareVolumeMaeData(yearData, "pitching", projectionSystems, pitchingVolumeStat);
    createChart("pitchingVolumeMaeChart", "bar", pitchingVolumeMaeData, `${pitchingVolumeLabel} MAE`, "MAE");
    const pitchingVolumeRmseData = prepareVolumeRmseData(yearData, "pitching", projectionSystems, pitchingVolumeStat);
    createChart("pitchingVolumeRmseChart", "bar", pitchingVolumeRmseData, `${pitchingVolumeLabel} RMSE`, "RMSE");

    // Individual pitching stat charts
    pitchingStats.forEach((statInfo) => {
      const cleanName = cleanStatName(statInfo.stat);

      // Raw MAE/RMSE
      const maeData = prepareStatSpecificData(yearData, "pitching", statInfo.stat, "MAE");
      if (maeData) {
        createChart(`pitching${cleanName}MaeChart`, "bar", maeData, `${statInfo.name} (${statInfo.stat}) Raw MAE`, "MAE");
      }

      const rmseData = prepareStatSpecificData(yearData, "pitching", statInfo.stat, "RMSE");
      if (rmseData) {
        createChart(`pitching${cleanName}RmseChart`, "bar", rmseData, `${statInfo.name} (${statInfo.stat}) Raw RMSE`, "RMSE");
      }

      // League-Adjusted MAE/RMSE
      const leagueAdjMaeData = prepareStatSpecificData(yearData, "pitching", statInfo.stat, "MAE", "league-adj");
      if (leagueAdjMaeData) {
        createChart(`pitching${cleanName}LeagueAdjMaeChart`, "bar", leagueAdjMaeData, `${statInfo.name} (${statInfo.stat}) League-Adjusted MAE`, "League-Adjusted MAE");
      }

      const leagueAdjRmseData = prepareStatSpecificData(yearData, "pitching", statInfo.stat, "RMSE", "league-adj");
      if (leagueAdjRmseData) {
        createChart(`pitching${cleanName}LeagueAdjRmseChart`, "bar", leagueAdjRmseData, `${statInfo.name} (${statInfo.stat}) League-Adjusted RMSE`, "League-Adjusted RMSE");
      }

      // Weighted League-Adjusted MAE/RMSE
      const wlaMaeData = prepareStatSpecificData(yearData, "pitching", statInfo.stat, "MAE", "weighted-league-adj");
      if (wlaMaeData) {
        createChart(`pitching${cleanName}WLAMaeChart`, "bar", wlaMaeData, `${statInfo.name} (${statInfo.stat}) Weighted LA MAE`, "Weighted LA MAE");
      }

      const wlaRmseData = prepareStatSpecificData(yearData, "pitching", statInfo.stat, "RMSE", "weighted-league-adj");
      if (wlaRmseData) {
        createChart(`pitching${cleanName}WLARmseChart`, "bar", wlaRmseData, `${statInfo.name} (${statInfo.stat}) Weighted LA RMSE`, "Weighted LA RMSE");
      }
    });
  }
}

function initializeFantasySeasonCharts(yearData, projectionSystems) {
  initializeSeasonCharts(yearData, projectionSystems, {
    battingStats: FANTASY_SEASON_BATTING_STATS,
    pitchingStats: FANTASY_SEASON_PITCHING_STATS,
    battingVolumeStat: "fan_PA",
    pitchingVolumeStat: "fan_BF",
    battingVolumeLabel: "Fantasy Batting PA",
    pitchingVolumeLabel: "Fantasy Pitching BF",
  });
}

const SUMMARY_METRIC_FIELDS = {
  MAE: { raw: "mae", "league-adj": "la_mae", "weighted-league-adj": "wla_mae" },
  RMSE: { raw: "rmse", "league-adj": "la_rmse", "weighted-league-adj": "wla_rmse" },
};

function summaryMetricValue(record, metric, adjustment, isVolume) {
  if (!record) return null;
  const field = SUMMARY_METRIC_FIELDS[metric][isVolume ? "raw" : adjustment];
  const value = record[field];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatSummaryError(value, isVolume) {
  if (value == null) return "-";
  if (isVolume) return value.toFixed(1);
  if (Math.abs(value) >= 1) return value.toFixed(3);
  return value.toFixed(4);
}

// Per column: best (lowest error) fades to 50% green, worst to 50% red, and the mean is uncolored.
function summaryHeatStyles(values) {
  const finite = values.filter((value) => value != null);
  const blank = "";
  if (finite.length === 0) return values.map(() => blank);

  const mean = finite.reduce((sum, value) => sum + value, 0) / finite.length;
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  const good = [22, 163, 74];
  const bad = [220, 38, 38];

  return values.map((value) => {
    if (value == null) return blank;

    let t = 0;
    let target = good;
    if (value < mean && mean > min) {
      t = (mean - value) / (mean - min);
    } else if (value > mean && max > mean) {
      t = (value - mean) / (max - mean);
      target = bad;
    }
    if (t < 0.02) return blank;

    const alpha = Math.min(0.5, t * 0.5);
    return `rgba(${target[0]}, ${target[1]}, ${target[2]}, ${alpha})`;
  });
}

// Lower error ranks first. Ties share the average of their positions. A missing category ranks last.
function summaryAverageRanks(valueRows) {
  const sums = valueRows.map(() => 0);

  if (valueRows.length === 0) return sums;
  const categoryCount = valueRows[0].length;

  for (let category = 0; category < categoryCount; category++) {
    const present = [];
    valueRows.forEach((values, rowIndex) => {
      const value = values[category];
      if (value != null) present.push({ rowIndex, value });
    });
    present.sort((a, b) => a.value - b.value);

    let start = 0;
    while (start < present.length) {
      let end = start + 1;
      while (end < present.length && present[end].value === present[start].value) end++;
      const rank = (start + 1 + end) / 2;
      for (let i = start; i < end; i++) sums[present[i].rowIndex] += rank;
      start = end;
    }

    const missingRank = present.length + 1;
    valueRows.forEach((values, rowIndex) => {
      if (values[category] == null) sums[rowIndex] += missingRank;
    });
  }

  return sums.map((sum) => sum / categoryCount);
}

function initializeSummaryTable(yearData, rootId = "fantasy-summary") {
  const root = document.getElementById(rootId);
  if (!root || !yearData) return;

  const metricSelect = root.querySelector(".summary-metric-select");
  const adjustmentSelect = root.querySelector(".summary-adjustment-select");
  const index = new Map();

  for (const playerType of ["batting", "pitching"]) {
    for (const record of yearData[playerType] || []) {
      index.set(`${playerType}|${record.system}|${record.stat}`, record);
    }
  }

  function render() {
    const metric = metricSelect.value;
    const adjustment = adjustmentSelect.value;
    const showRawTag = adjustment !== "raw";
    root.querySelectorAll(".summary-raw-tag").forEach((tag) => {
      tag.classList.toggle("hidden", !showRawTag);
    });

    root.querySelectorAll("table").forEach((table) => {
      const tbody = table.querySelector("tbody");
      const rows = [...tbody.querySelectorAll("tr")];
      const entries = rows.map((row) => {
        const cells = [...row.querySelectorAll(".summary-cell")];
        const values = cells.map((cell) => {
          const record = index.get(`${cell.dataset.playerType}|${row.dataset.system}|${cell.dataset.stat}`);
          return summaryMetricValue(record, metric, adjustment, cell.dataset.volume === "true");
        });
        return { row, cells, values };
      });

      const categoryCount = entries[0]?.values.length ?? 0;
      const bestRing = isDarkMode() ? "inset 0 0 0 2px #f8fafc" : "inset 0 0 0 2px #0f172a";
      for (let category = 0; category < categoryCount; category++) {
        const columnValues = entries.map((entry) => entry.values[category]);
        const backgrounds = summaryHeatStyles(columnValues);
        const finite = columnValues.filter((value) => value != null);
        const best = finite.length ? Math.min(...finite) : null;
        entries.forEach((entry, rowIndex) => {
          const cell = entry.cells[category];
          cell.textContent = formatSummaryError(entry.values[category], cell.dataset.volume === "true");
          cell.style.backgroundColor = backgrounds[rowIndex];
          cell.style.color = "";
          cell.style.boxShadow = entry.values[category] != null && entry.values[category] === best ? bestRing : "";
        });
      }

      const averageRanks = summaryAverageRanks(entries.map((entry) => entry.values));
      entries
        .map((entry, rowIndex) => ({ ...entry, averageRank: averageRanks[rowIndex] }))
        .sort((a, b) => a.averageRank - b.averageRank || Number(a.row.dataset.order) - Number(b.row.dataset.order))
        .forEach((entry) => {
          entry.row.hidden = entry.values.every((value) => value == null);
          tbody.appendChild(entry.row);
        });
    });
  }

  metricSelect.addEventListener("change", render);
  adjustmentSelect.addEventListener("change", render);
  new MutationObserver(render).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["class"],
  });
  render();
}
