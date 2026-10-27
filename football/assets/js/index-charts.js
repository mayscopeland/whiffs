function initializeIndexCharts(yearsData, projectionSystems, pools) {
  registerProjectionSystems(projectionSystems);
  if (!yearsData || Object.keys(yearsData).length === 0) return;
  statEntries(pools, false)
    .filter((stat) => stat.overview)
    .forEach((stat) => drawStatCharts(yearsData, projectionSystems, stat));
}
