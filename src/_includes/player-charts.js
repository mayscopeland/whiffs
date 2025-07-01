function initializePlayerCharts(playerYears, playerType, projectionSystems) {
    const statsToShow = playerType === 'batting' ?
        ['PA', 'SO/PA', 'BB/PA', 'HR/PA', 'HBP/PA'] :
        ['BF', 'SO/BF', 'BB/BF', 'HR/BF', 'HBP/BF'];

    // Create performance charts (actual vs projected)
    statsToShow.forEach(stat => {
        const chartData = preparePlayerStatChartData(playerYears, stat, playerType, projectionSystems);
        if (chartData.datasets && chartData.datasets.length > 0) {
            createChart(`rate${stat}Chart`, 'bar', chartData, `${stat} Over Time`, stat);
        }
    });

    // Create raw accuracy charts (RMSE)
    statsToShow.forEach(stat => {
        const chartData = preparePlayerAccuracyChartData(playerYears, stat, playerType, projectionSystems);
        if (chartData.datasets && chartData.datasets.length > 0) {
            createChart(`accuracy${stat}Chart`, 'line', chartData, `${stat} Projection Error (Raw RMSE)`, 'RMSE');
        }
    });

    // Create league-adjusted accuracy charts (RMSE) - only for rate stats
    const rateStatsOnly = playerType === 'batting' ?
        ['SO/PA', 'BB/PA', 'HR/PA', 'HBP/PA'] :
        ['SO/BF', 'BB/BF', 'HR/BF', 'HBP/BF'];

    rateStatsOnly.forEach(stat => {
        const chartData = preparePlayerLeagueAdjustedAccuracyChartData(playerYears, stat, playerType, projectionSystems);
        if (chartData.datasets && chartData.datasets.length > 0) {
            createChart(`accuracyLA${stat}Chart`, 'line', chartData, `${stat} Projection Error (League-Adjusted RMSE)`, 'League-Adjusted RMSE');
        }
    });
}