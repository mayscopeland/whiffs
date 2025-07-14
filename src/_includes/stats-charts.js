function initializeStatsCharts(yearsData, projectionSystems) {
  const battingStats = [
    { stat: "PA", baseName: "battingPA", name: "Plate Appearances", isVolume: true },
    { stat: "wOBA", baseName: "battingwOBA", name: "wOBA", isVolume: false },
    { stat: "SO/PA", baseName: "battingSO", name: "Strikeout Rate", isVolume: false },
    { stat: "BB/PA", baseName: "battingBB", name: "Walk Rate", isVolume: false },
    { stat: "HBP/PA", baseName: "battingHBP", name: "Hit By Pitch Rate", isVolume: false },
    { stat: "HR/BIP", baseName: "battingHR", name: "Home Run Rate", isVolume: false },
    { stat: "BABIP", baseName: "battingBABIP", name: "BABIP", isVolume: false },
    { stat: "1B/(BIP-HR)", baseName: "batting1B", name: "Single Rate", isVolume: false },
    { stat: "2B/(BIP-HR)", baseName: "batting2B", name: "Double Rate", isVolume: false },
    { stat: "3B/(BIP-HR)", baseName: "batting3B", name: "Triple Rate", isVolume: false },
    { stat: "R/PA", baseName: "battingR", name: "Run Rate", isVolume: false },
    { stat: "RBI/PA", baseName: "battingRBI", name: "RBI Rate", isVolume: false },
    { stat: "SB/TOF", baseName: "battingSB", name: "Stolen Base Rate", isVolume: false },
    { stat: "AVG", baseName: "battingAVG", name: "Batting Average", isVolume: false },
    { stat: "OBP", baseName: "battingOBP", name: "On-Base Percentage", isVolume: false },
    { stat: "SLG", baseName: "battingSLG", name: "Slugging Percentage", isVolume: false },
  ];

  const pitchingStats = [
    { stat: "BF", baseName: "pitchingBF", name: "Batters Faced", isVolume: true },
    { stat: "wOBA", baseName: "pitchingwOBA", name: "wOBA", isVolume: false },
    { stat: "SO/BF", baseName: "pitchingSO", name: "Strikeout Rate", isVolume: false },
    { stat: "BB/BF", baseName: "pitchingBB", name: "Walk Rate", isVolume: false },
    { stat: "HBP/BF", baseName: "pitchingHBP", name: "Hit By Pitch Rate", isVolume: false },
    { stat: "HR/BIP", baseName: "pitchingHR", name: "Home Run Rate", isVolume: false },
    { stat: "BABIP", baseName: "pitchingBABIP", name: "BABIP", isVolume: false },
    { stat: "1B/(BIP-HR)", baseName: "pitching1B", name: "Single Rate", isVolume: false },
    { stat: "2B/(BIP-HR)", baseName: "pitching2B", name: "Double Rate", isVolume: false },
    { stat: "3B/(BIP-HR)", baseName: "pitching3B", name: "Triple Rate", isVolume: false },
    { stat: "R/BF", baseName: "pitchingR", name: "Run Rate", isVolume: false },
    { stat: "ER/BF", baseName: "pitchingER", name: "Earned Run Rate", isVolume: false },
    { stat: "W/G", baseName: "pitchingW", name: "Win Rate", isVolume: false },
    { stat: "L/G", baseName: "pitchingL", name: "Loss Rate", isVolume: false },
    { stat: "SV/G", baseName: "pitchingSV", name: "Save Rate", isVolume: false },
    { stat: "HLD/G", baseName: "pitchingHLD", name: "Hold Rate", isVolume: false },
    { stat: "ERA", baseName: "pitchingERA", name: "ERA", isVolume: false },
    { stat: "WHIP", baseName: "pitchingWHIP", name: "WHIP", isVolume: false },
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
