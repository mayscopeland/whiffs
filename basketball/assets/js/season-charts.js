const DEFAULT_SEASON_STATS = [
  { name: "PTS/MIN", stat: "PTS/MIN", isVolume: false },
  { name: "OREB/MIN", stat: "OREB/MIN", isVolume: false },
  { name: "DREB/MIN", stat: "DREB/MIN", isVolume: false },
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

  function cleanStatName(stat) {
    return stat.replace(/[\/\(\)\-]/g, "");
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
  createChart("playerGMaeChart", "bar", prepareVolumeMaeData(yearData, "player", projectionSystems, "G"), "Games MAE", "MAE");
  createChart("playerGRmseChart", "bar", prepareVolumeRmseData(yearData, "player", projectionSystems, "G"), "Games RMSE", "RMSE");

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
