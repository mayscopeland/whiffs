function initializeIndexCharts(yearsData, projectionSystems) {
  const battingStats = [
    { stat: "PA", baseName: "battingPA", name: "Plate Appearances", isVolume: true },
    { stat: "wOBA", baseName: "battingwOBA", name: "wOBA", isVolume: false },
  ];

  const pitchingStats = [
    { stat: "BF", baseName: "pitchingBF", name: "Batters Faced", isVolume: true },
    { stat: "ERA", baseName: "pitchingERA", name: "ERA", isVolume: false },
  ];

  // Create batting charts
  battingStats.forEach(({ stat, baseName, name, isVolume }) => {
    if (isVolume) {
      // Volume stats: only create raw charts (no league adjustment)
      // 1. Raw MAE
      const rawMaeData = prepareStatMaeData(yearsData, stat, "batting", projectionSystems);
      createChart(`${baseName}MAEChart`, "line", rawMaeData, `${name} Raw MAE by Year`, "MAE");

      // 2. Raw RMSE
      const rawRmseData = prepareStatRmseData(yearsData, stat, "batting", projectionSystems);
      createChart(`${baseName}Chart`, "line", rawRmseData, `${name} Raw RMSE by Year`, "RMSE");
    } else {
      // Rate stats: create all 6 charts including weighted league-adjusted
      // 1. Weighted League-Adjusted MAE
      const weightedLeagueAdjMaeData = prepareStatWeightedLeagueAdjustedMaeData(yearsData, stat, "batting", projectionSystems);
      createChart(`${baseName}WeightedLeagueAdjMAEChart`, "line", weightedLeagueAdjMaeData, `${name} Weighted League-Adjusted MAE by Year`, "Weighted League-Adjusted MAE");

      // 2. League-Adjusted MAE
      const leagueAdjMaeData = prepareStatLeagueAdjustedMaeData(yearsData, stat, "batting", projectionSystems);
      createChart(`${baseName}LeagueAdjMAEChart`, "line", leagueAdjMaeData, `${name} League-Adjusted MAE by Year`, "League-Adjusted MAE");

      // 3. Raw MAE
      const rawMaeData = prepareStatMaeData(yearsData, stat, "batting", projectionSystems);
      createChart(`${baseName}MAEChart`, "line", rawMaeData, `${name} Raw MAE by Year`, "MAE");

      // 4. Weighted League-Adjusted RMSE
      const weightedLeagueAdjRmseData = prepareStatWeightedLeagueAdjustedRmseData(yearsData, stat, "batting", projectionSystems);
      createChart(`${baseName}WeightedLeagueAdjChart`, "line", weightedLeagueAdjRmseData, `${name} Weighted League-Adjusted RMSE by Year`, "Weighted League-Adjusted RMSE");

      // 5. League-Adjusted RMSE
      const leagueAdjRmseData = prepareStatLeagueAdjustedRmseData(yearsData, stat, "batting", projectionSystems);
      createChart(`${baseName}LeagueAdjChart`, "line", leagueAdjRmseData, `${name} League-Adjusted RMSE by Year`, "League-Adjusted RMSE");

      // 6. Raw RMSE
      const rawRmseData = prepareStatRmseData(yearsData, stat, "batting", projectionSystems);
      createChart(`${baseName}Chart`, "line", rawRmseData, `${name} Raw RMSE by Year`, "RMSE");
    }
  });

  // Create pitching charts
  pitchingStats.forEach(({ stat, baseName, name, isVolume }) => {
    if (isVolume) {
      // Volume stats: only create raw charts (no league adjustment)
      // 1. Raw MAE
      const rawMaeData = prepareStatMaeData(yearsData, stat, "pitching", projectionSystems);
      createChart(`${baseName}MAEChart`, "line", rawMaeData, `${name} Raw MAE by Year`, "MAE");

      // 2. Raw RMSE
      const rawRmseData = prepareStatRmseData(yearsData, stat, "pitching", projectionSystems);
      createChart(`${baseName}Chart`, "line", rawRmseData, `${name} Raw RMSE by Year`, "RMSE");
    } else {
      // Rate stats: create all 6 charts including weighted league-adjusted
      // 1. Weighted League-Adjusted MAE
      const weightedLeagueAdjMaeData = prepareStatWeightedLeagueAdjustedMaeData(yearsData, stat, "pitching", projectionSystems);
      createChart(`${baseName}WeightedLeagueAdjMAEChart`, "line", weightedLeagueAdjMaeData, `${name} Weighted League-Adjusted MAE by Year`, "Weighted League-Adjusted MAE");

      // 2. League-Adjusted MAE
      const leagueAdjMaeData = prepareStatLeagueAdjustedMaeData(yearsData, stat, "pitching", projectionSystems);
      createChart(`${baseName}LeagueAdjMAEChart`, "line", leagueAdjMaeData, `${name} League-Adjusted MAE by Year`, "League-Adjusted MAE");

      // 3. Raw MAE
      const rawMaeData = prepareStatMaeData(yearsData, stat, "pitching", projectionSystems);
      createChart(`${baseName}MAEChart`, "line", rawMaeData, `${name} Raw MAE by Year`, "MAE");

      // 4. Weighted League-Adjusted RMSE
      const weightedLeagueAdjRmseData = prepareStatWeightedLeagueAdjustedRmseData(yearsData, stat, "pitching", projectionSystems);
      createChart(`${baseName}WeightedLeagueAdjChart`, "line", weightedLeagueAdjRmseData, `${name} Weighted League-Adjusted RMSE by Year`, "Weighted League-Adjusted RMSE");

      // 5. League-Adjusted RMSE
      const leagueAdjRmseData = prepareStatLeagueAdjustedRmseData(yearsData, stat, "pitching", projectionSystems);
      createChart(`${baseName}LeagueAdjChart`, "line", leagueAdjRmseData, `${name} League-Adjusted RMSE by Year`, "League-Adjusted RMSE");

      // 6. Raw RMSE
      const rawRmseData = prepareStatRmseData(yearsData, stat, "pitching", projectionSystems);
      createChart(`${baseName}Chart`, "line", rawRmseData, `${name} Raw RMSE by Year`, "RMSE");
    }
  });
}
