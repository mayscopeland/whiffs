const DEFAULT_SEASON_STATS = [
  { name: "PTS/MIN", stat: "PTS/MIN", isVolume: false },
  { name: "OREB/MIN", stat: "OREB/MIN", isVolume: false },
  { name: "DREB/MIN", stat: "DREB/MIN", isVolume: false },
  { name: "REB/MIN", stat: "REB/MIN", isVolume: false },
  { name: "STL/MIN", stat: "STL/MIN", isVolume: false },
  { name: "AST/MIN", stat: "AST/MIN", isVolume: false },
  { name: "BLK/MIN", stat: "BLK/MIN", isVolume: false },
  { name: "FTA/MIN", stat: "FTA/MIN", isVolume: false },
  { name: "FGA/MIN", stat: "FGA/MIN", isVolume: false },
  { name: "3PA/MIN", stat: "FG3A/MIN", isVolume: false },
  { name: "TOV/MIN", stat: "TOV/MIN", isVolume: false },
  { name: "FT%", stat: "FTM/FTA", isVolume: false },
  { name: "FG%", stat: "FGM/FGA", isVolume: false },
  { name: "3P%", stat: "FG3M/FG3A", isVolume: false },
  { name: "3PA/FGA", stat: "FG3A/FGA", isVolume: false },
  { name: "MIN/G", stat: "MIN/G", isVolume: false },
];

function initializeSeasonCharts(yearData, projectionSystems, options = {}) {
  if (!yearData) {
    console.error("No data provided for this year.");
    return;
  }

  const playerStats = options.playerStats || DEFAULT_SEASON_STATS;
  const volumeStat = options.volumeStat || "MIN";
  const volumeLabel = options.volumeLabel || "Minutes";
  const gamesStat = options.gamesStat || "G";

  function cleanStatName(stat) {
    return String(stat).replace(/^fan_/, "").replace(/[\/\(\)\-]/g, "");
  }

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
          errorValue: value,
        };
      })
      .filter((dataset) => dataset.hasData)
      .sort((a, b) => {
        if (a.errorValue === null && b.errorValue === null) return 0;
        if (a.errorValue === null) return 1;
        if (b.errorValue === null) return -1;
        return b.errorValue - a.errorValue;
      });

    datasets.forEach((dataset) => {
      delete dataset.hasData;
      delete dataset.errorValue;
    });

    return { labels: [stat], datasets };
  }

  if (!yearData.player || yearData.player.length === 0) return;

  createChart("playerVolumeMaeChart", "bar", prepareVolumeMaeData(yearData, "player", projectionSystems, volumeStat), `${volumeLabel} MAE`, "MAE");
  createChart("playerVolumeRmseChart", "bar", prepareVolumeRmseData(yearData, "player", projectionSystems, volumeStat), `${volumeLabel} RMSE`, "RMSE");
  createChart("playerGMaeChart", "bar", prepareVolumeMaeData(yearData, "player", projectionSystems, gamesStat), "Games MAE", "MAE");
  createChart("playerGRmseChart", "bar", prepareVolumeRmseData(yearData, "player", projectionSystems, gamesStat), "Games RMSE", "RMSE");

  playerStats.forEach((statInfo) => {
    const cleanName = cleanStatName(statInfo.stat);
    const maeData = prepareStatSpecificData(yearData, "player", statInfo.stat, "MAE");
    if (maeData) createChart(`player${cleanName}MaeChart`, "bar", maeData, `${statInfo.name} Raw MAE`, "MAE");
    const rmseData = prepareStatSpecificData(yearData, "player", statInfo.stat, "RMSE");
    if (rmseData) createChart(`player${cleanName}RmseChart`, "bar", rmseData, `${statInfo.name} Raw RMSE`, "RMSE");
    const leagueAdjMaeData = prepareStatSpecificData(yearData, "player", statInfo.stat, "MAE", "league-adj");
    if (leagueAdjMaeData) createChart(`player${cleanName}LeagueAdjMaeChart`, "bar", leagueAdjMaeData, `${statInfo.name} League-Adjusted MAE`, "League-Adjusted MAE");
    const leagueAdjRmseData = prepareStatSpecificData(yearData, "player", statInfo.stat, "RMSE", "league-adj");
    if (leagueAdjRmseData) createChart(`player${cleanName}LeagueAdjRmseChart`, "bar", leagueAdjRmseData, `${statInfo.name} League-Adjusted RMSE`, "League-Adjusted RMSE");
    const wlaMaeData = prepareStatSpecificData(yearData, "player", statInfo.stat, "MAE", "weighted-league-adj");
    if (wlaMaeData) createChart(`player${cleanName}WLAMaeChart`, "bar", wlaMaeData, `${statInfo.name} Weighted LA MAE`, "Weighted LA MAE");
    const wlaRmseData = prepareStatSpecificData(yearData, "player", statInfo.stat, "RMSE", "weighted-league-adj");
    if (wlaRmseData) createChart(`player${cleanName}WLARmseChart`, "bar", wlaRmseData, `${statInfo.name} Weighted LA RMSE`, "Weighted LA RMSE");
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

function initializeSummaryTable(yearData, rootId = "season-summary", playerTypes = ["player"]) {
  const root = document.getElementById(rootId);
  if (!root || !yearData) return;

  const metricSelect = root.querySelector(".summary-metric-select");
  const adjustmentSelect = root.querySelector(".summary-adjustment-select");
  const index = new Map();

  for (const playerType of playerTypes) {
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
