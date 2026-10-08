const DEFAULT_PLAYER_STATS = [
  { stat: "MIN", baseName: "playerMIN", name: "Minutes", isVolume: true },
  { stat: "G", baseName: "playerG", name: "Games", isVolume: true },
  { stat: "PTS/MIN", baseName: "playerPTSMIN", name: "PTS/MIN", isVolume: false },
  { stat: "OREB/MIN", baseName: "playerOREBMIN", name: "OREB/MIN", isVolume: false },
  { stat: "DREB/MIN", baseName: "playerDREBMIN", name: "DREB/MIN", isVolume: false },
  { stat: "STL/MIN", baseName: "playerSTLMIN", name: "STL/MIN", isVolume: false },
  { stat: "AST/MIN", baseName: "playerASTMIN", name: "AST/MIN", isVolume: false },
  { stat: "BLK/MIN", baseName: "playerBLKMIN", name: "BLK/MIN", isVolume: false },
  { stat: "FTA/MIN", baseName: "playerFTAMIN", name: "FTA/MIN", isVolume: false },
  { stat: "FGA/MIN", baseName: "playerFGAMIN", name: "FGA/MIN", isVolume: false },
  { stat: "FG3A/MIN", baseName: "playerFG3AMIN", name: "3PA/MIN", isVolume: false },
  { stat: "TOV/MIN", baseName: "playerTOVMIN", name: "TOV/MIN", isVolume: false },
  { stat: "FTM/FTA", baseName: "playerFTPct", name: "FT%", isVolume: false },
  { stat: "FGM/FGA", baseName: "playerFGPct", name: "FG%", isVolume: false },
  { stat: "FG3M/FG3A", baseName: "playerFG3Pct", name: "3P%", isVolume: false },
  { stat: "FG3A/FGA", baseName: "playerFG3Rate", name: "3PA/FGA", isVolume: false },
  { stat: "MIN/G", baseName: "playerMING", name: "MIN/G", isVolume: false },
];

let lastStatsChartsOptions = {};

function initializeStatsCharts(yearsData, projectionSystems, options = lastStatsChartsOptions) {
  lastStatsChartsOptions = options || {};
  const playerStats = lastStatsChartsOptions.playerStats || DEFAULT_PLAYER_STATS;

  playerStats.forEach(({ stat, baseName, name, isVolume }) => {
    if (isVolume) {
      createChart(`${baseName}MAEChart`, "line", prepareStatMaeData(yearsData, stat, "player", projectionSystems), `${name} Raw MAE by Season`, "MAE");
      createChart(`${baseName}Chart`, "line", prepareStatRmseData(yearsData, stat, "player", projectionSystems), `${name} Raw RMSE by Season`, "RMSE");
      return;
    }
    createChart(`${baseName}WeightedLeagueAdjMAEChart`, "line", prepareStatWeightedLeagueAdjustedMaeData(yearsData, stat, "player", projectionSystems), `${name} Weighted League-Adjusted MAE by Season`, "Weighted League-Adjusted MAE");
    createChart(`${baseName}LeagueAdjMAEChart`, "line", prepareStatLeagueAdjustedMaeData(yearsData, stat, "player", projectionSystems), `${name} League-Adjusted MAE by Season`, "League-Adjusted MAE");
    createChart(`${baseName}MAEChart`, "line", prepareStatMaeData(yearsData, stat, "player", projectionSystems), `${name} Raw MAE by Season`, "MAE");
    createChart(`${baseName}WeightedLeagueAdjChart`, "line", prepareStatWeightedLeagueAdjustedRmseData(yearsData, stat, "player", projectionSystems), `${name} Weighted League-Adjusted RMSE by Season`, "Weighted League-Adjusted RMSE");
    createChart(`${baseName}LeagueAdjChart`, "line", prepareStatLeagueAdjustedRmseData(yearsData, stat, "player", projectionSystems), `${name} League-Adjusted RMSE by Season`, "League-Adjusted RMSE");
    createChart(`${baseName}Chart`, "line", prepareStatRmseData(yearsData, stat, "player", projectionSystems), `${name} Raw RMSE by Season`, "RMSE");
  });
}
