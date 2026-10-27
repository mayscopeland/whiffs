function cleanStatName(stat) {
  return String(stat).replace(/^fan_/, "").replace(/[\/\(\)\-]/g, "");
}

function drawStatCharts(yearsData, projectionSystems, statInfo) {
  const { stat, baseName, name, isVolume, playerType } = statInfo;
  if (isVolume) {
    createChart(`${baseName}MAEChart`, "line", prepareStatMaeData(yearsData, stat, playerType, projectionSystems), `${name} Raw MAE by Season`, "MAE");
    createChart(`${baseName}Chart`, "line", prepareStatRmseData(yearsData, stat, playerType, projectionSystems), `${name} Raw RMSE by Season`, "RMSE");
    return;
  }
  createChart(`${baseName}WeightedLeagueAdjMAEChart`, "line", prepareStatWeightedLeagueAdjustedMaeData(yearsData, stat, playerType, projectionSystems), `${name} Weighted League-Adjusted MAE by Season`, "Weighted League-Adjusted MAE");
  createChart(`${baseName}LeagueAdjMAEChart`, "line", prepareStatLeagueAdjustedMaeData(yearsData, stat, playerType, projectionSystems), `${name} League-Adjusted MAE by Season`, "League-Adjusted MAE");
  createChart(`${baseName}MAEChart`, "line", prepareStatMaeData(yearsData, stat, playerType, projectionSystems), `${name} Raw MAE by Season`, "MAE");
  createChart(`${baseName}WeightedLeagueAdjChart`, "line", prepareStatWeightedLeagueAdjustedRmseData(yearsData, stat, playerType, projectionSystems), `${name} Weighted League-Adjusted RMSE by Season`, "Weighted League-Adjusted RMSE");
  createChart(`${baseName}LeagueAdjChart`, "line", prepareStatLeagueAdjustedRmseData(yearsData, stat, playerType, projectionSystems), `${name} League-Adjusted RMSE by Season`, "League-Adjusted RMSE");
  createChart(`${baseName}Chart`, "line", prepareStatRmseData(yearsData, stat, playerType, projectionSystems), `${name} Raw RMSE by Season`, "RMSE");
}

function statEntries(pools, fantasy) {
  const entries = [];
  (pools || []).forEach((pool) => {
    const stats = [pool.volume, ...(pool.rates || [])];
    stats.forEach((stat) => {
      entries.push({
        stat: fantasy ? `fan_${stat.stat}` : stat.stat,
        baseName: stat.baseName,
        name: `${pool.label} ${stat.name}`,
        isVolume: !!stat.isVolume,
        playerType: pool.key,
        overview: !!stat.overview,
      });
    });
  });
  return entries;
}

function initializeStatsCharts(yearsData, projectionSystems, options = {}) {
  registerProjectionSystems(projectionSystems);
  if (!yearsData || Object.keys(yearsData).length === 0) return;
  const stats = options.playerStats || statEntries(options.pools || [], !!options.fantasy);
  stats.forEach((stat) => drawStatCharts(yearsData, projectionSystems, stat));
}
