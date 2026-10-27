function initializePlayerCharts(playerYears, projectionSystems, statsConfig) {
  registerProjectionSystems(projectionSystems);
  (statsConfig || []).forEach((statConfig) => {
    const idSafe = `${statConfig.playerType}${String(statConfig.stat).replace(/[\/\(\)\-]/g, "")}`;
    const playerType = statConfig.playerType;
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
