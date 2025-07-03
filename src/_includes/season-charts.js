function initializeSeasonCharts(yearData, projectionSystems) {
    if (!yearData) {
        console.error("No data provided for this year.");
        return;
    }

    // Define the stats arrays to match season.njk
    const battingStats = [
        { name: 'wOBA', stat: 'wOBA', isVolume: false },
        { name: 'Strikeout Rate', stat: 'SO/PA', isVolume: false },
        { name: 'Walk Rate', stat: 'BB/PA', isVolume: false },
        { name: 'Hit By Pitch Rate', stat: 'HBP/PA', isVolume: false },
        { name: 'Home Run Rate', stat: 'HR/BIP', isVolume: false },
        { name: 'BABIP', stat: 'BABIP', isVolume: false },
        { name: 'Single Rate', stat: '1B/(BIP-HR)', isVolume: false },
        { name: 'Double Rate', stat: '2B/(BIP-HR)', isVolume: false },
        { name: 'Triple Rate', stat: '3B/(BIP-HR)', isVolume: false },
        { name: 'Run Rate', stat: 'R/PA', isVolume: false },
        { name: 'RBI Rate', stat: 'RBI/PA', isVolume: false },
        { name: 'Stolen Base Rate', stat: 'SB/TOF', isVolume: false },
        { name: 'Batting Average', stat: 'AVG', isVolume: false },
        { name: 'On-Base Percentage', stat: 'OBP', isVolume: false },
        { name: 'Slugging Percentage', stat: 'SLG', isVolume: false }
    ];

    const pitchingStats = [
        { name: 'wOBA', stat: 'wOBA', isVolume: false },
        { name: 'Strikeout Rate', stat: 'SO/BF', isVolume: false },
        { name: 'Walk Rate', stat: 'BB/BF', isVolume: false },
        { name: 'Hit By Pitch Rate', stat: 'HBP/BF', isVolume: false },
        { name: 'Home Run Rate', stat: 'HR/BIP', isVolume: false },
        { name: 'BABIP', stat: 'BABIP', isVolume: false },
        { name: 'Single Rate', stat: '1B/(BIP-HR)', isVolume: false },
        { name: 'Double Rate', stat: '2B/(BIP-HR)', isVolume: false },
        { name: 'Triple Rate', stat: '3B/(BIP-HR)', isVolume: false },
        { name: 'Run Rate', stat: 'R/BF', isVolume: false },
        { name: 'Earned Run Rate', stat: 'ER/BF', isVolume: false },
        { name: 'Win Rate', stat: 'W/G', isVolume: false },
        { name: 'Loss Rate', stat: 'L/G', isVolume: false },
        { name: 'Save Rate', stat: 'SV/G', isVolume: false },
        { name: 'Hold Rate', stat: 'HLD/G', isVolume: false },
        { name: 'ERA', stat: 'ERA', isVolume: false },
        { name: 'WHIP', stat: 'WHIP', isVolume: false }
    ];

    // Helper function to clean stat names for chart IDs
    function cleanStatName(stat) {
        return stat.replace(/[\/\(\)\-]/g, '');
    }

    // Helper function to prepare stat-specific data
    function prepareStatSpecificData(yearData, playerType, stat, dataType, adjustment = null) {
        const results = yearData[playerType] || [];
        const statData = results.filter(result => result.stat === stat);

        if (statData.length === 0) return null;

        const datasets = projectionSystems.map(system => {
            const systemData = statData.find(result => result.system === system);
            let value = 0;

            if (systemData) {
                if (adjustment === 'league-adj') {
                    value = dataType === 'MAE' ? systemData.la_mae : systemData.la_rmse;
                } else if (adjustment === 'weighted-league-adj') {
                    value = dataType === 'MAE' ? systemData.wla_mae : systemData.wla_rmse;
                } else {
                    value = dataType === 'MAE' ? systemData.mae : systemData.rmse;
                }
            }

            return {
                label: system,
                data: [value || 0],
                backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
                borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
                borderWidth: 1
            };
        });

        return {
            labels: [stat],
            datasets: datasets
        };
    }

    // Batting Charts
    if (yearData.batting && yearData.batting.length > 0) {
        // Volume MAE/RMSE
        const battingVolumeMaeData = prepareVolumeMaeData(yearData, 'batting', projectionSystems);
        createChart('battingVolumeMaeChart', 'bar', battingVolumeMaeData, 'Batting PA MAE', 'MAE');
        const battingVolumeRmseData = prepareVolumeRmseData(yearData, 'batting', projectionSystems);
        createChart('battingVolumeRmseChart', 'bar', battingVolumeRmseData, 'Batting PA RMSE', 'RMSE');

        // Individual batting stat charts
        battingStats.forEach(statInfo => {
            const cleanName = cleanStatName(statInfo.stat);

            // Raw MAE/RMSE
            const maeData = prepareStatSpecificData(yearData, 'batting', statInfo.stat, 'MAE');
            if (maeData) {
                createChart(`batting${cleanName}MaeChart`, 'bar', maeData, `${statInfo.name} (${statInfo.stat}) Raw MAE`, 'MAE');
            }

            const rmseData = prepareStatSpecificData(yearData, 'batting', statInfo.stat, 'RMSE');
            if (rmseData) {
                createChart(`batting${cleanName}RmseChart`, 'bar', rmseData, `${statInfo.name} (${statInfo.stat}) Raw RMSE`, 'RMSE');
            }

            // League-Adjusted MAE/RMSE
            const leagueAdjMaeData = prepareStatSpecificData(yearData, 'batting', statInfo.stat, 'MAE', 'league-adj');
            if (leagueAdjMaeData) {
                createChart(`batting${cleanName}LeagueAdjMaeChart`, 'bar', leagueAdjMaeData, `${statInfo.name} (${statInfo.stat}) League-Adjusted MAE`, 'League-Adjusted MAE');
            }

            const leagueAdjRmseData = prepareStatSpecificData(yearData, 'batting', statInfo.stat, 'RMSE', 'league-adj');
            if (leagueAdjRmseData) {
                createChart(`batting${cleanName}LeagueAdjRmseChart`, 'bar', leagueAdjRmseData, `${statInfo.name} (${statInfo.stat}) League-Adjusted RMSE`, 'League-Adjusted RMSE');
            }

            // Weighted League-Adjusted MAE/RMSE
            const wlaMaeData = prepareStatSpecificData(yearData, 'batting', statInfo.stat, 'MAE', 'weighted-league-adj');
            if (wlaMaeData) {
                createChart(`batting${cleanName}WLAMaeChart`, 'bar', wlaMaeData, `${statInfo.name} (${statInfo.stat}) Weighted LA MAE`, 'Weighted LA MAE');
            }

            const wlaRmseData = prepareStatSpecificData(yearData, 'batting', statInfo.stat, 'RMSE', 'weighted-league-adj');
            if (wlaRmseData) {
                createChart(`batting${cleanName}WLARmseChart`, 'bar', wlaRmseData, `${statInfo.name} (${statInfo.stat}) Weighted LA RMSE`, 'Weighted LA RMSE');
            }
        });
    }

    // Pitching Charts
    if (yearData.pitching && yearData.pitching.length > 0) {
        // Volume MAE/RMSE
        const pitchingVolumeMaeData = prepareVolumeMaeData(yearData, 'pitching', projectionSystems);
        createChart('pitchingVolumeMaeChart', 'bar', pitchingVolumeMaeData, 'Pitching BF MAE', 'MAE');
        const pitchingVolumeRmseData = prepareVolumeRmseData(yearData, 'pitching', projectionSystems);
        createChart('pitchingVolumeRmseChart', 'bar', pitchingVolumeRmseData, 'Pitching BF RMSE', 'RMSE');

        // Individual pitching stat charts
        pitchingStats.forEach(statInfo => {
            const cleanName = cleanStatName(statInfo.stat);

            // Raw MAE/RMSE
            const maeData = prepareStatSpecificData(yearData, 'pitching', statInfo.stat, 'MAE');
            if (maeData) {
                createChart(`pitching${cleanName}MaeChart`, 'bar', maeData, `${statInfo.name} (${statInfo.stat}) Raw MAE`, 'MAE');
            }

            const rmseData = prepareStatSpecificData(yearData, 'pitching', statInfo.stat, 'RMSE');
            if (rmseData) {
                createChart(`pitching${cleanName}RmseChart`, 'bar', rmseData, `${statInfo.name} (${statInfo.stat}) Raw RMSE`, 'RMSE');
            }

            // League-Adjusted MAE/RMSE
            const leagueAdjMaeData = prepareStatSpecificData(yearData, 'pitching', statInfo.stat, 'MAE', 'league-adj');
            if (leagueAdjMaeData) {
                createChart(`pitching${cleanName}LeagueAdjMaeChart`, 'bar', leagueAdjMaeData, `${statInfo.name} (${statInfo.stat}) League-Adjusted MAE`, 'League-Adjusted MAE');
            }

            const leagueAdjRmseData = prepareStatSpecificData(yearData, 'pitching', statInfo.stat, 'RMSE', 'league-adj');
            if (leagueAdjRmseData) {
                createChart(`pitching${cleanName}LeagueAdjRmseChart`, 'bar', leagueAdjRmseData, `${statInfo.name} (${statInfo.stat}) League-Adjusted RMSE`, 'League-Adjusted RMSE');
            }

            // Weighted League-Adjusted MAE/RMSE
            const wlaMaeData = prepareStatSpecificData(yearData, 'pitching', statInfo.stat, 'MAE', 'weighted-league-adj');
            if (wlaMaeData) {
                createChart(`pitching${cleanName}WLAMaeChart`, 'bar', wlaMaeData, `${statInfo.name} (${statInfo.stat}) Weighted LA MAE`, 'Weighted LA MAE');
            }

            const wlaRmseData = prepareStatSpecificData(yearData, 'pitching', statInfo.stat, 'RMSE', 'weighted-league-adj');
            if (wlaRmseData) {
                createChart(`pitching${cleanName}WLARmseChart`, 'bar', wlaRmseData, `${statInfo.name} (${statInfo.stat}) Weighted LA RMSE`, 'Weighted LA RMSE');
            }
        });
    }
}