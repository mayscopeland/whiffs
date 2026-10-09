let exclude2020 = true;

const projectionSystemColors = {
  "SPS": "#8c564b",
  "ESPN": "#d62728",
};

const projectionSystemBorderColors = {
  "SPS": "#8c564b",
  "ESPN": "#d62728",
};

function endYearToSeason(endYear) {
  const end = parseInt(endYear, 10);
  if (Number.isNaN(end)) return String(endYear);
  return `${end - 1}-${String(end).slice(-2)}`;
}

const defaultColor = "#7f7f7f";
const _allCharts = [];

function isDarkMode() {
  return document.documentElement.classList.contains('dark');
}

function applyThemeDefaults() {
  const dark = isDarkMode();
  Chart.defaults.color = dark ? '#e2e8f0' : '#64748b';                    // text: slate-200 vs slate-500
  Chart.defaults.borderColor = dark ? 'rgba(148, 163, 184, 0.2)' : 'rgba(0, 0, 0, 0.1)';  // grid lines
}

function getBarBorderColor() {
  return isDarkMode() ? '#64748b' : '#0f172a';
}

// Apply theme defaults on load
applyThemeDefaults();


function filterYearsData(yearsData) {
  if (!exclude2020) {
    return yearsData;
  }

  const filteredData = {};
  for (const [year, data] of Object.entries(yearsData)) {
    if (year !== "2020") {
      filteredData[year] = data;
    } else {
      // Keep 2020 but nullify the data to create a break in the chart
      filteredData[year] = {
        player: data.player?.map((item) => ({ ...item, rmse: null, mae: null, la_rmse: null, la_mae: null, wla_rmse: null, wla_mae: null })) || [],
      };
    }
  }
  return filteredData;
}

function filterPlayerYearsData(playerYears) {
  if (!exclude2020) {
    return playerYears;
  }

  const filteredData = {};
  for (const [year, data] of Object.entries(playerYears)) {
    if (year !== "2020") {
      filteredData[year] = data;
    } else {
      // Keep 2020 but nullify the data to create a break in the chart
      const nullifiedData = {};
      for (const [playerType, systems] of Object.entries(data)) {
        nullifiedData[playerType] = {};
        for (const [system, stats] of Object.entries(systems)) {
          nullifiedData[playerType][system] = {};
          for (const [stat, value] of Object.entries(stats)) {
            nullifiedData[playerType][system][stat] = null;
          }
        }
      }
      filteredData[year] = nullifiedData;
    }
  }
  return filteredData;
}

function prepareStatRmseData(yearsData, stat, playerType, projectionSystems) {
  const filteredYearsData = filterYearsData(yearsData);
  const years = Object.keys(filteredYearsData).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const datasets = projectionSystems.map((system) => {
    const data = years.map((year) => {
      const yearData = filteredYearsData[year];
      if (!yearData || !yearData[playerType]) return null;
      const result = yearData[playerType].find((r) => r.system === system && r.stat === stat);
      return result && !isNaN(result.rmse) ? result.rmse : null;
    });
    return {
      label: system,
      data: data,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      borderWidth: 2,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets };
}

function prepareStatLeagueAdjustedRmseData(yearsData, stat, playerType, projectionSystems) {
  const filteredYearsData = filterYearsData(yearsData);
  const years = Object.keys(filteredYearsData).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const datasets = projectionSystems.map((system) => {
    const data = years.map((year) => {
      const yearData = filteredYearsData[year];
      if (!yearData || !yearData[playerType]) return null;
      const result = yearData[playerType].find((r) => r.system === system && r.stat === stat);
      return result && !isNaN(result.la_rmse) ? result.la_rmse : null;
    });
    return {
      label: system,
      data: data,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      borderWidth: 2,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets };
}

function prepareStatMaeData(yearsData, stat, playerType, projectionSystems) {
  const filteredYearsData = filterYearsData(yearsData);
  const years = Object.keys(filteredYearsData).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const datasets = projectionSystems.map((system) => {
    const data = years.map((year) => {
      const yearData = filteredYearsData[year];
      if (!yearData || !yearData[playerType]) return null;
      const result = yearData[playerType].find((r) => r.system === system && r.stat === stat);
      return result && !isNaN(result.mae) ? result.mae : null;
    });
    return {
      label: system,
      data: data,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      borderWidth: 2,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets };
}

function prepareStatLeagueAdjustedMaeData(yearsData, stat, playerType, projectionSystems) {
  const filteredYearsData = filterYearsData(yearsData);
  const years = Object.keys(filteredYearsData).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const datasets = projectionSystems.map((system) => {
    const data = years.map((year) => {
      const yearData = filteredYearsData[year];
      if (!yearData || !yearData[playerType]) return null;
      const result = yearData[playerType].find((r) => r.system === system && r.stat === stat);
      return result && !isNaN(result.la_mae) ? result.la_mae : null;
    });
    return {
      label: system,
      data: data,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      borderWidth: 2,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets };
}

function prepareVolumeRmseData(yearData, playerType, projectionSystems, volumeStat = null) {
  const volumeStats = [volumeStat || "MIN"];
  const stats = volumeStats.filter((stat) => yearData[playerType] && yearData[playerType].some((r) => r.stat === stat));

  const datasets = projectionSystems
    .map((system) => {
      const data = stats.map((stat) => {
        const result = yearData[playerType].find((r) => r.stat === stat && r.system === system);
        return result ? result.rmse : null;
      });

      // Check if this system has any data for any stat
      const hasData = data.some((value) => value !== null);

      return {
        label: system,
        data: data,
        backgroundColor: projectionSystemColors[system] || defaultColor,
        borderColor: projectionSystemBorderColors[system] || defaultColor,
        borderWidth: 2,
        hasData: hasData,
        errorValue: data[0], // Use the first (and only) stat's error value for sorting
      };
    })
    .filter((dataset) => dataset.hasData)
    .sort((a, b) => {
      // Sort by error value in descending order (worst to best)
      // Handle null values by putting them at the end
      if (a.errorValue === null && b.errorValue === null) return 0;
      if (a.errorValue === null) return 1;
      if (b.errorValue === null) return -1;
      return b.errorValue - a.errorValue;
    });

  // Remove the hasData and errorValue properties before returning
  datasets.forEach((dataset) => {
    delete dataset.hasData;
    delete dataset.errorValue;
  });

  return { labels: stats, datasets };
}

/**
 * Prepare volume MAE data for a specific year (for season pages)
 */
function prepareVolumeMaeData(yearData, playerType, projectionSystems, volumeStat = null) {
  const volumeStats = [volumeStat || "MIN"];
  const stats = volumeStats.filter((stat) => yearData[playerType] && yearData[playerType].some((r) => r.stat === stat));

  const datasets = projectionSystems
    .map((system) => {
      const data = stats.map((stat) => {
        const result = yearData[playerType].find((r) => r.stat === stat && r.system === system);
        return result ? result.mae : null;
      });

      // Check if this system has any data for any stat
      const hasData = data.some((value) => value !== null);

      return {
        label: system,
        data: data,
        backgroundColor: projectionSystemColors[system] || defaultColor,
        borderColor: projectionSystemBorderColors[system] || defaultColor,
        borderWidth: 2,
        hasData: hasData,
        errorValue: data[0], // Use the first (and only) stat's error value for sorting
      };
    })
    .filter((dataset) => dataset.hasData)
    .sort((a, b) => {
      // Sort by error value in descending order (worst to best)
      // Handle null values by putting them at the end
      if (a.errorValue === null && b.errorValue === null) return 0;
      if (a.errorValue === null) return 1;
      if (b.errorValue === null) return -1;
      return b.errorValue - a.errorValue;
    });

  // Remove the hasData and errorValue properties before returning
  datasets.forEach((dataset) => {
    delete dataset.hasData;
    delete dataset.errorValue;
  });

  return { labels: stats, datasets };
}


function preparePlayerAccuracyChartData(playerYears, stat, playerType, projectionSystems) {
  if (!playerYears || typeof playerYears !== "object") {
    return { labels: [], datasets: [] };
  }
  const filteredPlayerYears = filterPlayerYearsData(playerYears);
  const years = Object.keys(filteredPlayerYears).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const projSystems = projectionSystems.filter((s) => s !== "Actual");
  const datasets = projSystems.map((system) => {
    const errorData = years.map((year) => {
      const yearData = filteredPlayerYears[year];
      if (yearData && yearData[playerType] && yearData[playerType]["Actual"] && yearData[playerType][system]) {
        const actual = yearData[playerType]["Actual"][stat];
        const projected = yearData[playerType][system][stat];
        if (actual != null && projected != null) {
          return Math.abs(projected - actual);
        }
      }
      return null;
    });

    return {
      label: system,
      data: errorData,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      borderWidth: 2,
      fill: false,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets: datasets.filter((d) => d.data.some((v) => v !== null)) };
}

function preparePlayerAccuracyMaeChartData(playerYears, stat, playerType, projectionSystems) {
  if (!playerYears || typeof playerYears !== "object") {
    return { labels: [], datasets: [] };
  }
  const filteredPlayerYears = filterPlayerYearsData(playerYears);
  const years = Object.keys(filteredPlayerYears).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const projSystems = projectionSystems.filter((s) => s !== "Actual");
  const datasets = projSystems.map((system) => {
    const errorData = years.map((year) => {
      const yearData = filteredPlayerYears[year];
      if (yearData && yearData[playerType] && yearData[playerType]["Actual"] && yearData[playerType][system]) {
        const actual = yearData[playerType]["Actual"][stat];
        const projected = yearData[playerType][system][stat];
        if (actual != null && projected != null) {
          return Math.abs(projected - actual);
        }
      }
      return null;
    });

    return {
      label: system,
      data: errorData,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      borderWidth: 2,
      fill: false,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets: datasets.filter((d) => d.data.some((v) => v !== null)) };
}

function preparePlayerLeagueAdjustedAccuracyChartData(playerYears, stat, playerType, projectionSystems) {
  const filteredPlayerYears = filterPlayerYearsData(playerYears);
  const years = Object.keys(filteredPlayerYears).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const datasets = projectionSystems.map((system) => {
    const data = years.map((year) => {
      const yearData = filteredPlayerYears[year];
      if (!yearData || !yearData[playerType] || !yearData[playerType][system] || !yearData[playerType]["Actual"]) {
        return null;
      }

      // Get pre-calculated league-adjusted values
      const projected_la = yearData[playerType][system][`${stat}_la`];
      const actual_la = yearData[playerType]["Actual"][`${stat}_la`];

      if (projected_la === undefined || actual_la === undefined || projected_la === null || actual_la === null) {
        return null;
      }

      // The league-adjusted error is the difference between the projected LA value and the actual LA value
      const la_error = projected_la - actual_la;
      return la_error;
    });

    return {
      label: system,
      data: data.map((e) => (e !== null ? Math.abs(e) : null)),
      fill: false,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderWidth: 2,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets: datasets.filter((d) => d.data.some((v) => v !== null)) };
}

function preparePlayerLeagueAdjustedAccuracyMaeChartData(playerYears, stat, playerType, projectionSystems) {
  const filteredPlayerYears = filterPlayerYearsData(playerYears);
  const years = Object.keys(filteredPlayerYears).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const datasets = projectionSystems.map((system) => {
    const data = years.map((year) => {
      const yearData = filteredPlayerYears[year];
      if (!yearData || !yearData[playerType] || !yearData[playerType][system] || !yearData[playerType]["Actual"]) {
        return null;
      }

      // Get pre-calculated league-adjusted values
      const projected_la = yearData[playerType][system][`${stat}_la`];
      const actual_la = yearData[playerType]["Actual"][`${stat}_la`];

      if (projected_la === undefined || actual_la === undefined || projected_la === null || actual_la === null) {
        return null;
      }

      // The league-adjusted error is the difference between the projected LA value and the actual LA value
      const la_error = projected_la - actual_la;
      return la_error;
    });

    return {
      label: system,
      data: data.map((e) => (e !== null ? Math.abs(e) : null)),
      fill: false,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderWidth: 2,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets: datasets.filter((d) => d.data.some((v) => v !== null)) };
}

function prepareStatWeightedLeagueAdjustedRmseData(yearsData, stat, playerType, projectionSystems) {
  const filteredYearsData = filterYearsData(yearsData);
  const years = Object.keys(filteredYearsData).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const datasets = projectionSystems.map((system) => {
    const data = years.map((year) => {
      const yearData = filteredYearsData[year];
      if (!yearData || !yearData[playerType]) return null;
      const result = yearData[playerType].find((r) => r.system === system && r.stat === stat);
      return result && !isNaN(result.wla_rmse) ? result.wla_rmse : null;
    });
    return {
      label: system,
      data: data,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      borderWidth: 2,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets };
}

function prepareStatWeightedLeagueAdjustedMaeData(yearsData, stat, playerType, projectionSystems) {
  const filteredYearsData = filterYearsData(yearsData);
  const years = Object.keys(filteredYearsData).sort();
  const yearLabels = years.map((y) => endYearToSeason(y));

  const datasets = projectionSystems.map((system) => {
    const data = years.map((year) => {
      const yearData = filteredYearsData[year];
      if (!yearData || !yearData[playerType]) return null;
      const result = yearData[playerType].find((r) => r.system === system && r.stat === stat);
      return result && !isNaN(result.wla_mae) ? result.wla_mae : null;
    });
    return {
      label: system,
      data: data,
      backgroundColor: projectionSystemColors[system] || defaultColor,
      borderColor: projectionSystemBorderColors[system] || defaultColor,
      borderWidth: 2,
      tension: 0.4,
      pointRadius: 4,
      pointHoverRadius: 6,
    };
  });

  return { labels: yearLabels, datasets };
}

function createChart(canvasId, type, data, title, yAxisLabel = "RMSE") {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return null;

  // Use scriptable borderColor for bar charts so it updates with theme
  if (type === 'bar') {
    data.datasets.forEach(dataset => {
      dataset.borderColor = () => getBarBorderColor();
      dataset.borderWidth = 2;
    });
  }

  // Scriptable color functions — re-evaluated on each render
  const gridColor = () => isDarkMode() ? 'rgba(148, 163, 184, 0.2)' : 'rgba(0, 0, 0, 0.1)';
  const textColor = () => isDarkMode() ? '#e2e8f0' : '#1e293b';

  const chart = new Chart(canvas.getContext("2d"), {
    type: type,
    data: data,
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 1000,
        easing: 'easeOutQuart',
      },
      interaction: {
        mode: "nearest",
        intersect: false,
      },
      onHover: (event, activeElements, chart) => {
        // Only apply hover effects for line charts
        if (type === "line") {
          const datasets = chart.data.datasets;

          if (activeElements.length > 0) {
            // Get the hovered dataset index
            const hoveredDatasetIndex = activeElements[0].datasetIndex;

            // Update all datasets
            datasets.forEach((dataset, index) => {
              // Get the original color for this system
              const originalColor = projectionSystemColors[dataset.label] || defaultColor;

              if (index === hoveredDatasetIndex) {
                // Brighten the hovered line and show data points
                dataset.backgroundColor = originalColor;
                dataset.borderColor = originalColor;
              } else {
                // Dim other lines by adding transparency
                dataset.backgroundColor = originalColor + "4D";
                dataset.borderColor = originalColor + "4D";
              }
            });
          } else {
            // Reset all datasets to normal when not hovering
            datasets.forEach((dataset) => {
              // Reset to original colors and default point settings
              const originalColor = projectionSystemColors[dataset.label] || defaultColor;
              dataset.backgroundColor = originalColor;
              dataset.borderColor = originalColor;
            });
          }

          chart.update("none"); // Update without animation for smooth interaction
        }
      },
      scales: {
        y: {
          beginAtZero: false,
          grid: {
            color: gridColor,
          },
          ticks: {
            color: textColor,
          },
          title: {
            display: true,
            text: yAxisLabel,
            color: textColor,
          },
        },
        x: {
          grid: {
            color: gridColor,
          },
          ticks: {
            color: textColor,
          },
          title: {
            display: true,
            text: type === "bar" ? (title.includes("Over Time") ? "Year" : "") : "Year",
            color: textColor,
          },
        },
      },
      plugins: {
        title: {
          display: true,
          text: title,
          color: textColor,
        },
        legend: {
          display: true,
          position: "top",
          labels: {
            color: textColor,
          },
        },
      },
    },
  });

  // Store chart instance globally if chartInstances exists
  if (typeof chartInstances !== "undefined") {
    chartInstances[canvasId] = chart;
  }

  // Also track in local registry for theme updates
  _allCharts.push(chart);

  return chart;
}

// Update all chart instances when dark mode toggles
function updateChartsTheme() {
  applyThemeDefaults();

  _allCharts.forEach(chart => {
    if (!chart || !chart.canvas) return; // skip destroyed charts
    chart.update('none');
  });
}

// Watch for dark mode class changes on <html>
const themeObserver = new MutationObserver((mutations) => {
  for (const mutation of mutations) {
    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
      requestAnimationFrame(() => updateChartsTheme());
      break;
    }
  }
});
if (document.documentElement) {
  themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
}

