
function initializeIndexCharts(yearsData, projectionSystems) {
    const battingStats = [
        { stat: 'PA', baseName: 'battingPA', title: 'Plate Appearances', isVolumestat: true },
        { stat: 'SO/PA', baseName: 'battingSO', title: 'Strikeout Rate', isVolumestat: false },
        { stat: 'BB/PA', baseName: 'battingBB', title: 'Walk Rate', isVolumestat: false },
        { stat: 'HR/PA', baseName: 'battingHR', title: 'Home Run Rate', isVolumestat: false },
        { stat: 'HBP/PA', baseName: 'battingHBP', title: 'Hit By Pitch Rate', isVolumestat: false }
    ];

    const pitchingStats = [
        { stat: 'BF', baseName: 'pitchingBF', title: 'Batters Faced', isVolumestat: true },
        { stat: 'SO/BF', baseName: 'pitchingSO', title: 'Strikeout Rate', isVolumestat: false },
        { stat: 'BB/BF', baseName: 'pitchingBB', title: 'Walk Rate', isVolumestat: false },
        { stat: 'HR/BF', baseName: 'pitchingHR', title: 'Home Run Rate', isVolumestat: false },
        { stat: 'HBP/BF', baseName: 'pitchingHBP', title: 'Hit By Pitch Rate', isVolumestat: false }
    ];

    // Create batting charts
    battingStats.forEach(({ stat, baseName, title, isVolumestat }) => {
        if (isVolumestat) {
            // Volume stats: only create raw charts (no league adjustment)
            // 1. Raw MAE
            const rawMaeData = prepareStatMaeData(yearsData, stat, 'batting', projectionSystems);
            createChart(`${baseName}MAEChart`, 'line', rawMaeData, `${title} Raw MAE by Year`, 'MAE');

            // 2. Raw RMSE
            const rawRmseData = prepareStatRmseData(yearsData, stat, 'batting', projectionSystems);
            createChart(`${baseName}Chart`, 'line', rawRmseData, `${title} Raw RMSE by Year`, 'RMSE');
        } else {
            // Rate stats: create all 6 charts including weighted league-adjusted
            // 1. Weighted League-Adjusted MAE
            const weightedLeagueAdjMaeData = prepareStatWeightedLeagueAdjustedMaeData(yearsData, stat, 'batting', projectionSystems);
            createChart(`${baseName}WeightedLeagueAdjMAEChart`, 'line', weightedLeagueAdjMaeData, `${title} Weighted League-Adjusted MAE by Year`, 'Weighted League-Adjusted MAE');

            // 2. League-Adjusted MAE
            const leagueAdjMaeData = prepareStatLeagueAdjustedMaeData(yearsData, stat, 'batting', projectionSystems);
            createChart(`${baseName}LeagueAdjMAEChart`, 'line', leagueAdjMaeData, `${title} League-Adjusted MAE by Year`, 'League-Adjusted MAE');

            // 3. Raw MAE
            const rawMaeData = prepareStatMaeData(yearsData, stat, 'batting', projectionSystems);
            createChart(`${baseName}MAEChart`, 'line', rawMaeData, `${title} Raw MAE by Year`, 'MAE');

            // 4. Weighted League-Adjusted RMSE
            const weightedLeagueAdjRmseData = prepareStatWeightedLeagueAdjustedRmseData(yearsData, stat, 'batting', projectionSystems);
            createChart(`${baseName}WeightedLeagueAdjChart`, 'line', weightedLeagueAdjRmseData, `${title} Weighted League-Adjusted RMSE by Year`, 'Weighted League-Adjusted RMSE');

            // 5. League-Adjusted RMSE
            const leagueAdjRmseData = prepareStatLeagueAdjustedRmseData(yearsData, stat, 'batting', projectionSystems);
            createChart(`${baseName}LeagueAdjChart`, 'line', leagueAdjRmseData, `${title} League-Adjusted RMSE by Year`, 'League-Adjusted RMSE');

            // 6. Raw RMSE
            const rawRmseData = prepareStatRmseData(yearsData, stat, 'batting', projectionSystems);
            createChart(`${baseName}Chart`, 'line', rawRmseData, `${title} Raw RMSE by Year`, 'RMSE');
        }
    });

    // Create pitching charts
    pitchingStats.forEach(({ stat, baseName, title, isVolumestat }) => {
        if (isVolumestat) {
            // Volume stats: only create raw charts (no league adjustment)
            // 1. Raw MAE
            const rawMaeData = prepareStatMaeData(yearsData, stat, 'pitching', projectionSystems);
            createChart(`${baseName}MAEChart`, 'line', rawMaeData, `${title} Raw MAE by Year`, 'MAE');

            // 2. Raw RMSE
            const rawRmseData = prepareStatRmseData(yearsData, stat, 'pitching', projectionSystems);
            createChart(`${baseName}Chart`, 'line', rawRmseData, `${title} Raw RMSE by Year`, 'RMSE');
        } else {
            // Rate stats: create all 6 charts including weighted league-adjusted
            // 1. Weighted League-Adjusted MAE
            const weightedLeagueAdjMaeData = prepareStatWeightedLeagueAdjustedMaeData(yearsData, stat, 'pitching', projectionSystems);
            createChart(`${baseName}WeightedLeagueAdjMAEChart`, 'line', weightedLeagueAdjMaeData, `${title} Weighted League-Adjusted MAE by Year`, 'Weighted League-Adjusted MAE');

            // 2. League-Adjusted MAE
            const leagueAdjMaeData = prepareStatLeagueAdjustedMaeData(yearsData, stat, 'pitching', projectionSystems);
            createChart(`${baseName}LeagueAdjMAEChart`, 'line', leagueAdjMaeData, `${title} League-Adjusted MAE by Year`, 'League-Adjusted MAE');

            // 3. Raw MAE
            const rawMaeData = prepareStatMaeData(yearsData, stat, 'pitching', projectionSystems);
            createChart(`${baseName}MAEChart`, 'line', rawMaeData, `${title} Raw MAE by Year`, 'MAE');

            // 4. Weighted League-Adjusted RMSE
            const weightedLeagueAdjRmseData = prepareStatWeightedLeagueAdjustedRmseData(yearsData, stat, 'pitching', projectionSystems);
            createChart(`${baseName}WeightedLeagueAdjChart`, 'line', weightedLeagueAdjRmseData, `${title} Weighted League-Adjusted RMSE by Year`, 'Weighted League-Adjusted RMSE');

            // 5. League-Adjusted RMSE
            const leagueAdjRmseData = prepareStatLeagueAdjustedRmseData(yearsData, stat, 'pitching', projectionSystems);
            createChart(`${baseName}LeagueAdjChart`, 'line', leagueAdjRmseData, `${title} League-Adjusted RMSE by Year`, 'League-Adjusted RMSE');

            // 6. Raw RMSE
            const rawRmseData = prepareStatRmseData(yearsData, stat, 'pitching', projectionSystems);
            createChart(`${baseName}Chart`, 'line', rawRmseData, `${title} Raw RMSE by Year`, 'RMSE');
        }
    });
}