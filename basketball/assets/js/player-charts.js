const PLAYER_STATS_CONFIG = [
  { name: "Minutes", stat: "MIN", isVolume: true },
  { name: "Games", stat: "G", isVolume: true },
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

function initializePlayerCharts(playerYears, playerType, projectionSystems) {
  PLAYER_STATS_CONFIG.forEach((statConfig) => {
    const idSafe = statConfig.stat.replace(/[\/\(\)\-]/g, "");
    if (statConfig.isVolume) {
      const rmseData = preparePlayerAccuracyChartData(playerYears, statConfig.stat, playerType, projectionSystems);
      if (rmseData.datasets && rmseData.datasets.length > 0) {
        createChart(`accuracy${idSafe}RMSEChart`, "line", rmseData, `${statConfig.name} - Raw Absolute Error`, "Absolute Error");
      }
      const maeData = preparePlayerAccuracyMaeChartData(playerYears, statConfig.stat, playerType, projectionSystems);
      if (maeData.datasets && maeData.datasets.length > 0) {
        createChart(`accuracy${idSafe}MAEChart`, "line", maeData, `${statConfig.name} - Raw Absolute Error`, "Absolute Error");
      }
      return;
    }

    const rmseData = preparePlayerAccuracyChartData(playerYears, statConfig.stat, playerType, projectionSystems);
    if (rmseData.datasets && rmseData.datasets.length > 0) {
      createChart(`accuracy${idSafe}RMSEChart`, "line", rmseData, `${statConfig.name} - Raw Absolute Error`, "Absolute Error");
    }
    const rmseLa = preparePlayerLeagueAdjustedAccuracyChartData(playerYears, statConfig.stat, playerType, projectionSystems);
    if (rmseLa.datasets && rmseLa.datasets.length > 0) {
      createChart(`accuracyLA${idSafe}RMSEChart`, "line", rmseLa, `${statConfig.name} - League-Adjusted Absolute Error`, "League-Adjusted Absolute Error");
    }
    const maeData = preparePlayerAccuracyMaeChartData(playerYears, statConfig.stat, playerType, projectionSystems);
    if (maeData.datasets && maeData.datasets.length > 0) {
      createChart(`accuracy${idSafe}MAEChart`, "line", maeData, `${statConfig.name} - Raw Absolute Error`, "Absolute Error");
    }
    const maeLa = preparePlayerLeagueAdjustedAccuracyMaeChartData(playerYears, statConfig.stat, playerType, projectionSystems);
    if (maeLa.datasets && maeLa.datasets.length > 0) {
      createChart(`accuracyLA${idSafe}MAEChart`, "line", maeLa, `${statConfig.name} - League-Adjusted Absolute Error`, "League-Adjusted Absolute Error");
    }
  });
}
