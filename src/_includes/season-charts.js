function initializeSeasonCharts(yearData, projectionSystems) {
    if (!yearData) {
        console.error("No data provided for this year.");
        return;
    }

    // Batting Charts
    if (yearData.batting && yearData.batting.length > 0) {
        // Volume MAE/RMSE
        const battingVolumeMaeData = prepareVolumeMaeData(yearData, 'batting', projectionSystems);
        createChart('battingVolumeMaeChart', 'bar', battingVolumeMaeData, 'Batting PA MAE', 'MAE');
        const battingVolumeRmseData = prepareVolumeRmseData(yearData, 'batting', projectionSystems);
        createChart('battingVolumeRmseChart', 'bar', battingVolumeRmseData, 'Batting PA RMSE', 'RMSE');

        // Rate MAE/RMSE (all versions)
        const battingRateMaeData = prepareRateMaeData(yearData, 'batting', projectionSystems);
        createChart('battingRateMaeChart', 'bar', battingRateMaeData, 'Batting Rate MAE', 'MAE');
        const battingRateRmseData = prepareRateRmseData(yearData, 'batting', projectionSystems);
        createChart('battingRateRmseChart', 'bar', battingRateRmseData, 'Batting Rate RMSE', 'RMSE');

        const battingRateLeagueAdjMaeData = prepareRateLeagueAdjustedMaeData(yearData, 'batting', projectionSystems);
        createChart('battingRateLeagueAdjMaeChart', 'bar', battingRateLeagueAdjMaeData, 'Batting Rate League-Adjusted MAE', 'League-Adjusted MAE');
        const battingRateLeagueAdjRmseData = prepareRateLeagueAdjustedRmseData(yearData, 'batting', projectionSystems);
        createChart('battingRateLeagueAdjRmseChart', 'bar', battingRateLeagueAdjRmseData, 'Batting Rate League-Adjusted RMSE', 'League-Adjusted RMSE');

        const battingRateWLAMaeData = prepareRateWeightedLeagueAdjustedMaeData(yearData, 'batting', projectionSystems);
        createChart('battingRateWLAMaeChart', 'bar', battingRateWLAMaeData, 'Batting Rate Weighted LA MAE', 'Weighted LA MAE');
        const battingRateWLARmseData = prepareRateWeightedLeagueAdjustedRmseData(yearData, 'batting', projectionSystems);
        createChart('battingRateWLARmseChart', 'bar', battingRateWLARmseData, 'Batting Rate Weighted LA RMSE', 'Weighted LA RMSE');
    }

    // Pitching Charts
    if (yearData.pitching && yearData.pitching.length > 0) {
        // Volume MAE/RMSE
        const pitchingVolumeMaeData = prepareVolumeMaeData(yearData, 'pitching', projectionSystems);
        createChart('pitchingVolumeMaeChart', 'bar', pitchingVolumeMaeData, 'Pitching BF MAE', 'MAE');
        const pitchingVolumeRmseData = prepareVolumeRmseData(yearData, 'pitching', projectionSystems);
        createChart('pitchingVolumeRmseChart', 'bar', pitchingVolumeRmseData, 'Pitching BF RMSE', 'RMSE');

        // Rate MAE/RMSE (all versions)
        const pitchingRateMaeData = prepareRateMaeData(yearData, 'pitching', projectionSystems);
        createChart('pitchingRateMaeChart', 'bar', pitchingRateMaeData, 'Pitching Rate MAE', 'MAE');
        const pitchingRateRmseData = prepareRateRmseData(yearData, 'pitching', projectionSystems);
        createChart('pitchingRateRmseChart', 'bar', pitchingRateRmseData, 'Pitching Rate RMSE', 'RMSE');

        const pitchingRateLeagueAdjMaeData = prepareRateLeagueAdjustedMaeData(yearData, 'pitching', projectionSystems);
        createChart('pitchingRateLeagueAdjMaeChart', 'bar', pitchingRateLeagueAdjMaeData, 'Pitching Rate League-Adjusted MAE', 'League-Adjusted MAE');
        const pitchingRateLeagueAdjRmseData = prepareRateLeagueAdjustedRmseData(yearData, 'pitching', projectionSystems);
        createChart('pitchingRateLeagueAdjRmseChart', 'bar', pitchingRateLeagueAdjRmseData, 'Pitching Rate League-Adjusted RMSE', 'League-Adjusted RMSE');

        const pitchingRateWLAMaeData = prepareRateWeightedLeagueAdjustedMaeData(yearData, 'pitching', projectionSystems);
        createChart('pitchingRateWLAMaeChart', 'bar', pitchingRateWLAMaeData, 'Pitching Rate Weighted LA MAE', 'Weighted LA MAE');
        const pitchingRateWLARmseData = prepareRateWeightedLeagueAdjustedRmseData(yearData, 'pitching', projectionSystems);
        createChart('pitchingRateWLARmseChart', 'bar', pitchingRateWLARmseData, 'Pitching Rate Weighted LA RMSE', 'Weighted LA RMSE');
    }
}