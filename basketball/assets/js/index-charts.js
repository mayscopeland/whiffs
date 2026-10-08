function initializeIndexCharts(yearsData, projectionSystems) {
  const overviewStats = [
    { stat: "MIN", baseName: "playerMIN", name: "Minutes", isVolume: true },
    { stat: "PTS/MIN", baseName: "playerPTSMIN", name: "PTS/MIN", isVolume: false },
    { stat: "FGM/FGA", baseName: "playerFGPct", name: "FG%", isVolume: false },
  ];

  overviewStats.forEach(({ stat, baseName, name, isVolume }) => {
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
