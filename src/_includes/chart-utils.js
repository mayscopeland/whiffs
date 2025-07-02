// Chart utility functions for MLB projection evaluation
// Replaces Python chart generation logic

const projectionSystemColors = {
    'Marcel': 'rgba(239, 68, 68, 0.8)', // red-500
    'Steamer': 'rgba(99, 102, 241, 0.8)', // indigo-500
    'ZiPS': 'rgba(34, 197, 94, 0.8)', // green-500
};

const projectionSystemBorderColors = {
    'Marcel': 'rgba(239, 68, 68, 1)',
    'Steamer': 'rgba(99, 102, 241, 1)',
    'ZiPS': 'rgba(34, 197, 94, 1)',
};

/**
 * Prepare RMSE data for a specific stat over time (for index page)
 */
function prepareStatRmseData(yearsData, stat, playerType, projectionSystems) {
    const years = Object.keys(yearsData).sort();
    const yearLabels = years.map(y => y.toString());

    const datasets = projectionSystems.map(system => {
        const data = years.map(year => {
            const yearData = yearsData[year];
            if (!yearData || !yearData[playerType]) return null;
            const result = yearData[playerType].find(r => r.system === system && r.stat === stat);
            return result && !isNaN(result.rmse) ? result.rmse : null;
        });
        return {
            label: system,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: yearLabels, datasets };
}

/**
 * Prepare league-adjusted RMSE data for a specific stat over time (for index page)
 */
function prepareStatLeagueAdjustedRmseData(yearsData, stat, playerType, projectionSystems) {
    const years = Object.keys(yearsData).sort();
    const yearLabels = years.map(y => y.toString());

    const datasets = projectionSystems.map(system => {
        const data = years.map(year => {
            const yearData = yearsData[year];
            if (!yearData || !yearData[playerType]) return null;
            const result = yearData[playerType].find(r => r.system === system && r.stat === stat);
            return result && !isNaN(result.la_rmse) ? result.la_rmse : null;
        });
        return {
            label: `${system} (League-Adjusted)`,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: yearLabels, datasets };
}

/**
 * Prepare MAE data for a specific stat over time (for index page)
 */
function prepareStatMaeData(yearsData, stat, playerType, projectionSystems) {
    const years = Object.keys(yearsData).sort();
    const yearLabels = years.map(y => y.toString());

    const datasets = projectionSystems.map(system => {
        const data = years.map(year => {
            const yearData = yearsData[year];
            if (!yearData || !yearData[playerType]) return null;
            const result = yearData[playerType].find(r => r.system === system && r.stat === stat);
            return result && !isNaN(result.mae) ? result.mae : null;
        });
        return {
            label: system,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: yearLabels, datasets };
}

/**
 * Prepare league-adjusted MAE data for a specific stat over time (for index page)
 */
function prepareStatLeagueAdjustedMaeData(yearsData, stat, playerType, projectionSystems) {
    const years = Object.keys(yearsData).sort();
    const yearLabels = years.map(y => y.toString());

    const datasets = projectionSystems.map(system => {
        const data = years.map(year => {
            const yearData = yearsData[year];
            if (!yearData || !yearData[playerType]) return null;
            const result = yearData[playerType].find(r => r.system === system && r.stat === stat);
            return result && !isNaN(result.la_mae) ? result.la_mae : null;
        });
        return {
            label: `${system} (League-Adjusted)`,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: yearLabels, datasets };
}

/**
 * Prepare volume RMSE data for a specific year (for season pages)
 */
function prepareVolumeRmseData(yearData, playerType, projectionSystems) {
    const volumeStats = playerType === 'batting' ? ['PA'] : ['BF'];
    const stats = volumeStats.filter(stat =>
        yearData[playerType] && yearData[playerType].some(r => r.stat === stat)
    );

    const datasets = projectionSystems.map(system => {
        const data = stats.map(stat => {
            const result = yearData[playerType].find(r => r.stat === stat && r.system === system);
            return result ? result.rmse : 0;
        });
        return {
            label: system,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: stats, datasets };
}

/**
 * Prepare rate RMSE data for a specific year (for season pages)
 */
function prepareRateRmseData(yearData, playerType, projectionSystems) {
    const rateStats = playerType === 'batting' ?
        ['SO/PA', 'BB/PA', 'HR/PA', 'HBP/PA'] :
        ['SO/BF', 'BB/BF', 'HR/BF', 'HBP/BF'];

    const stats = rateStats.filter(stat =>
        yearData[playerType] && yearData[playerType].some(r => r.stat === stat)
    );

    const datasets = projectionSystems.map(system => {
        const data = stats.map(stat => {
            const result = yearData[playerType].find(r => r.stat === stat && r.system === system);
            return result ? result.rmse : 0;
        });
        return {
            label: system,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: stats, datasets };
}

/**
 * Prepare league-adjusted volume RMSE data for a specific year (for season pages)
 */
function prepareVolumeLeagueAdjustedRmseData(yearData, playerType, projectionSystems) {
    const volumeStats = playerType === 'batting' ? ['PA'] : ['BF'];
    const stats = volumeStats.filter(stat =>
        yearData[playerType] && yearData[playerType].some(r => r.stat === stat)
    );

    const datasets = projectionSystems.map(system => {
        const data = stats.map(stat => {
            const result = yearData[playerType].find(r => r.stat === stat && r.system === system);
            return result ? result.la_rmse : 0;
        });
        return {
            label: `${system} (LA)`,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: stats, datasets };
}

/**
 * Prepare league-adjusted rate RMSE data for a specific year (for season pages)
 */
function prepareRateLeagueAdjustedRmseData(yearData, playerType, projectionSystems) {
    const rateStats = playerType === 'batting' ?
        ['SO/PA', 'BB/PA', 'HR/PA', 'HBP/PA'] :
        ['SO/BF', 'BB/BF', 'HR/BF', 'HBP/BF'];
    const stats = rateStats.filter(stat =>
        yearData[playerType] && yearData[playerType].some(r => r.stat === stat)
    );

    const datasets = projectionSystems.map(system => {
        const data = stats.map(stat => {
            const result = yearData[playerType].find(r => r.stat === stat && r.system === system);
            return result ? result.la_rmse : 0;
        });
        return {
            label: `${system} (LA)`,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: stats, datasets };
}

/**
 * Prepare volume MAE data for a specific year (for season pages)
 */
function prepareVolumeMaeData(yearData, playerType, projectionSystems) {
    const volumeStats = playerType === 'batting' ? ['PA'] : ['BF'];
    const stats = volumeStats.filter(stat =>
        yearData[playerType] && yearData[playerType].some(r => r.stat === stat)
    );

    const datasets = projectionSystems.map(system => {
        const data = stats.map(stat => {
            const result = yearData[playerType].find(r => r.stat === stat && r.system === system);
            return result ? result.mae : 0;
        });
        return {
            label: system,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: stats, datasets };
}

/**
 * Prepare rate MAE data for a specific year (for season pages)
 */
function prepareRateMaeData(yearData, playerType, projectionSystems) {
    const rateStats = playerType === 'batting' ?
        ['SO/PA', 'BB/PA', 'HR/PA', 'HBP/PA'] :
        ['SO/BF', 'BB/BF', 'HR/BF', 'HBP/BF'];
    const stats = rateStats.filter(stat =>
        yearData[playerType] && yearData[playerType].some(r => r.stat === stat)
    );

    const datasets = projectionSystems.map(system => {
        const data = stats.map(stat => {
            const result = yearData[playerType].find(r => r.stat === stat && r.system === system);
            return result ? result.mae : 0;
        });
        return {
            label: system,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: stats, datasets };
}

/**
 * Prepare league-adjusted rate MAE data for a specific year (for season pages)
 */
function prepareRateLeagueAdjustedMaeData(yearData, playerType, projectionSystems) {
    const rateStats = playerType === 'batting' ?
        ['SO/PA', 'BB/PA', 'HR/PA', 'HBP/PA'] :
        ['SO/BF', 'BB/BF', 'HR/BF', 'HBP/BF'];
    const stats = rateStats.filter(stat =>
        yearData[playerType] && yearData[playerType].some(r => r.stat === stat)
    );

    const datasets = projectionSystems.map(system => {
        const data = stats.map(stat => {
            const result = yearData[playerType].find(r => r.stat === stat && r.system === system);
            return result ? result.la_mae : 0;
        });
        return {
            label: `${system} (LA)`,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: stats, datasets };
}

/**
 * Prepare weighted league-adjusted rate RMSE data for a specific year (for season pages)
 */
function prepareRateWeightedLeagueAdjustedRmseData(yearData, playerType, projectionSystems) {
    const rateStats = playerType === 'batting' ?
        ['SO/PA', 'BB/PA', 'HR/PA', 'HBP/PA'] :
        ['SO/BF', 'BB/BF', 'HR/BF', 'HBP/BF'];
    const stats = rateStats.filter(stat =>
        yearData[playerType] && yearData[playerType].some(r => r.stat === stat)
    );

    const datasets = projectionSystems.map(system => {
        const data = stats.map(stat => {
            const result = yearData[playerType].find(r => r.stat === stat && r.system === system);
            return result ? result.wla_rmse : 0;
        });
        return {
            label: `${system} (WLA)`,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: stats, datasets };
}

/**
 * Prepare weighted league-adjusted rate MAE data for a specific year (for season pages)
 */
function prepareRateWeightedLeagueAdjustedMaeData(yearData, playerType, projectionSystems) {
    const rateStats = playerType === 'batting' ?
        ['SO/PA', 'BB/PA', 'HR/PA', 'HBP/PA'] :
        ['SO/BF', 'BB/BF', 'HR/BF', 'HBP/BF'];
    const stats = rateStats.filter(stat =>
        yearData[playerType] && yearData[playerType].some(r => r.stat === stat)
    );

    const datasets = projectionSystems.map(system => {
        const data = stats.map(stat => {
            const result = yearData[playerType].find(r => r.stat === stat && r.system === system);
            return result ? result.wla_mae : 0;
        });
        return {
            label: `${system} (WLA)`,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: stats, datasets };
}

/**
 * Prepare data for a player stat chart over their career
 */
function preparePlayerStatChartData(playerYears, stat, playerType, projectionSystems) {
    if (!playerYears || typeof playerYears !== 'object') {
        return { labels: [], datasets: [] };
    }
    const years = Object.keys(playerYears).sort();
    const yearLabels = years.map(y => y.toString());

    const datasets = [];

    // Create a dataset for actual performance
    const actualData = years.map(year => {
        const yearData = playerYears[year];
        if (yearData && yearData[playerType] && yearData[playerType]['Actual']) {
            return yearData[playerType]['Actual'][stat] ?? null;
        }
        return null;
    });

    datasets.push({
        label: 'Actual',
        data: actualData,
        backgroundColor: 'rgba(55, 65, 81, 0.8)', // gray-700
        borderColor: 'rgba(55, 65, 81, 1)',
        borderWidth: 1,
        type: 'line',
        order: 0
    });

    // Create datasets for each projection system
    const projSystems = projectionSystems.filter(s => s !== 'Actual');
    projSystems.forEach(system => {
        const projData = years.map(year => {
            const yearData = playerYears[year];
            if (yearData && yearData[playerType] && yearData[playerType][system]) {
                return yearData[playerType][system][stat] ?? null;
            }
            return null;
        });

        datasets.push({
            label: system,
            data: projData,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1,
            type: 'bar',
            order: 1
        });
    });

    return { labels: yearLabels, datasets };
}

/**
 * Prepare data for a player accuracy chart over their career
 */
function preparePlayerAccuracyChartData(playerYears, stat, playerType, projectionSystems) {
    if (!playerYears || typeof playerYears !== 'object') {
        return { labels: [], datasets: [] };
    }
    const years = Object.keys(playerYears).sort();
    const yearLabels = years.map(y => y.toString());

    const projSystems = projectionSystems.filter(s => s !== 'Actual');
    const datasets = projSystems.map(system => {
        const errorData = years.map(year => {
            const yearData = playerYears[year];
            if (yearData && yearData[playerType] && yearData[playerType]['Actual'] && yearData[playerType][system]) {
                const actual = yearData[playerType]['Actual'][stat];
                const projected = yearData[playerType][system][stat];
                if (actual != null && projected != null) {
                    return Math.abs(projected - actual);
                }
            }
            return null;
        });

        return {
            label: `${system} Error`,
            data: errorData,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            fill: false
        };
    });

    return { labels: yearLabels, datasets: datasets.filter(d => d.data.some(v => v !== null)) };
}

/**
 * Prepare league-adjusted accuracy data (error) for a specific player (for player pages)
 */
function preparePlayerLeagueAdjustedAccuracyChartData(playerYears, stat, playerType, projectionSystems) {
    const years = Object.keys(playerYears).sort();
    const yearLabels = years.map(y => y.toString());

    const datasets = projectionSystems.map(system => {
        const data = years.map(year => {
            const yearData = playerYears[year];
            if (!yearData || !yearData[playerType] || !yearData[playerType][system] || !yearData[playerType]['Actual']) {
                return null;
            }

            // Get pre-calculated league-adjusted values
            const projected_la = yearData[playerType][system][`${stat}_la`];
            const actual_la = yearData[playerType]['Actual'][`${stat}_la`];

            if (projected_la === undefined || actual_la === undefined || projected_la === null || actual_la === null) {
                return null;
            }

            // The league-adjusted error is the difference between the projected LA value and the actual LA value
            const la_error = projected_la - actual_la;
            return la_error;
        });

        return {
            label: system,
            data: data.map(e => (e !== null ? Math.abs(e) : null)),
            fill: false,
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            tension: 0.1
        };
    });

    return { labels: yearLabels, datasets: datasets.filter(d => d.data.some(v => v !== null)) };
}

/**
 * Prepare weighted league-adjusted RMSE data for a specific stat over time (for index page)
 */
function prepareStatWeightedLeagueAdjustedRmseData(yearsData, stat, playerType, projectionSystems) {
    const years = Object.keys(yearsData).sort();
    const yearLabels = years.map(y => y.toString());

    const datasets = projectionSystems.map(system => {
        const data = years.map(year => {
            const yearData = yearsData[year];
            if (!yearData || !yearData[playerType]) return null;
            const result = yearData[playerType].find(r => r.system === system && r.stat === stat);
            return result && !isNaN(result.wla_rmse) ? result.wla_rmse : null;
        });
        return {
            label: `${system} (WLA)`,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: yearLabels, datasets };
}

/**
 * Prepare weighted league-adjusted MAE data for a specific stat over time (for index page)
 */
function prepareStatWeightedLeagueAdjustedMaeData(yearsData, stat, playerType, projectionSystems) {
    const years = Object.keys(yearsData).sort();
    const yearLabels = years.map(y => y.toString());

    const datasets = projectionSystems.map(system => {
        const data = years.map(year => {
            const yearData = yearsData[year];
            if (!yearData || !yearData[playerType]) return null;
            const result = yearData[playerType].find(r => r.system === system && r.stat === stat);
            return result && !isNaN(result.wla_mae) ? result.wla_mae : null;
        });
        return {
            label: `${system} (WLA)`,
            data: data,
            backgroundColor: projectionSystemColors[system] || 'rgba(156, 163, 175, 0.8)',
            borderColor: projectionSystemBorderColors[system] || 'rgba(156, 163, 175, 1)',
            borderWidth: 1
        };
    });

    return { labels: yearLabels, datasets };
}

/**
 * Create a Chart.js chart with standard options
 */
function createChart(canvasId, type, data, title, yAxisLabel = 'RMSE') {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return null;

    return new Chart(canvas.getContext('2d'), {
        type: type,
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: false,
                    title: {
                        display: true,
                        text: yAxisLabel
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: type === 'bar' ? (title.includes('Over Time') ? 'Year' : 'Stat') : 'Year'
                    }
                }
            },
            plugins: {
                title: {
                    display: true,
                    text: title
                },
                legend: {
                    display: true,
                    position: 'top'
                }
            }
        }
    });
}