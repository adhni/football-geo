(function () {
  "use strict";

  // Keep the provider in one place for explorers, comparisons and profiles.
  // Browser caching and a valid Referer are required by the OSM tile policy:
  // https://operations.osmfoundation.org/policies/tiles/
  const provider = {
    url: "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
    maxZoom: 19,
  };

  function create(appearance = "dark") {
    return L.tileLayer(provider.url, {
      attribution: provider.attribution,
      maxZoom: provider.maxZoom,
      className: appearance === "dark" ? "talent-basemap-dark" : "talent-basemap-light",
      referrerPolicy: "strict-origin-when-cross-origin",
      updateWhenIdle: true,
      updateWhenZooming: false,
      keepBuffer: 1,
    });
  }

  window.TalentGeoBasemap = { create };
}());
