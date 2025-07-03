function initializePlayerCharts(playerYears, playerType, projectionSystems) {
    const statsConfig = playerType === 'batting' ? [
        { name: 'Plate Appearances', stat: 'PA', isVolume: true },
        { name: 'Strikeout Rate', stat: 'SO/PA', isVolume: false },
        { name: 'Walk Rate', stat: 'BB/PA', isVolume: false },
        { name: 'Home Run Rate', stat: 'HR/PA', isVolume: false },
        { name: 'Hit By Pitch Rate', stat: 'HBP/PA', isVolume: false }
    ] : [
        { name: 'Batters Faced', stat: 'BF', isVolume: true },
        { name: 'Strikeout Rate', stat: 'SO/BF', isVolume: false },
        { name: 'Walk Rate', stat: 'BB/BF', isVolume: false },
        { name: 'Home Run Rate', stat: 'HR/BF', isVolume: false },
        { name: 'Hit By Pitch Rate', stat: 'HBP/BF', isVolume: false }
    ];

    // Create performance charts (actual vs projected)
    statsConfig.forEach(statConfig => {
        const chartData = preparePlayerStatChartData(playerYears, statConfig.stat, playerType, projectionSystems);
        if (chartData.datasets && chartData.datasets.length > 0) {
            createChart(`rate${statConfig.stat}Chart`, 'bar', chartData, `${statConfig.stat} Over Time`, statConfig.stat);
        }
    });

    // Create accuracy charts for all stats and metrics
    statsConfig.forEach(statConfig => {
        // RMSE charts
        if (statConfig.isVolume) {
            // Volume stats: only raw RMSE
            const rmseData = preparePlayerAccuracyChartData(playerYears, statConfig.stat, playerType, projectionSystems);
            if (rmseData.datasets && rmseData.datasets.length > 0) {
                createChart(`accuracy${statConfig.stat}RMSEChart`, 'line', rmseData, `${statConfig.name} (${statConfig.stat}) - Raw RMSE Error`, 'RMSE');
            }
        } else {
            // Rate stats: both raw and league-adjusted RMSE
            const rmseData = preparePlayerAccuracyChartData(playerYears, statConfig.stat, playerType, projectionSystems);
            if (rmseData.datasets && rmseData.datasets.length > 0) {
                createChart(`accuracy${statConfig.stat}RMSEChart`, 'line', rmseData, `${statConfig.name} (${statConfig.stat}) - Raw RMSE Error`, 'RMSE');
            }

            const rmseLeagueAdjData = preparePlayerLeagueAdjustedAccuracyChartData(playerYears, statConfig.stat, playerType, projectionSystems);
            if (rmseLeagueAdjData.datasets && rmseLeagueAdjData.datasets.length > 0) {
                createChart(`accuracyLA${statConfig.stat}RMSEChart`, 'line', rmseLeagueAdjData, `${statConfig.name} (${statConfig.stat}) - League-Adjusted RMSE Error`, 'League-Adjusted RMSE');
            }
        }

        // MAE charts
        if (statConfig.isVolume) {
            // Volume stats: only raw MAE
            const maeData = preparePlayerAccuracyMaeChartData(playerYears, statConfig.stat, playerType, projectionSystems);
            if (maeData.datasets && maeData.datasets.length > 0) {
                createChart(`accuracy${statConfig.stat}MAEChart`, 'line', maeData, `${statConfig.name} (${statConfig.stat}) - Raw MAE Error`, 'MAE');
            }
        } else {
            // Rate stats: both raw and league-adjusted MAE
            const maeData = preparePlayerAccuracyMaeChartData(playerYears, statConfig.stat, playerType, projectionSystems);
            if (maeData.datasets && maeData.datasets.length > 0) {
                createChart(`accuracy${statConfig.stat}MAEChart`, 'line', maeData, `${statConfig.name} (${statConfig.stat}) - Raw MAE Error`, 'MAE');
            }

            const maeLeagueAdjData = preparePlayerLeagueAdjustedAccuracyMaeChartData(playerYears, statConfig.stat, playerType, projectionSystems);
            if (maeLeagueAdjData.datasets && maeLeagueAdjData.datasets.length > 0) {
                createChart(`accuracyLA${statConfig.stat}MAEChart`, 'line', maeLeagueAdjData, `${statConfig.name} (${statConfig.stat}) - League-Adjusted MAE Error`, 'League-Adjusted MAE');
            }
        }
    });
}