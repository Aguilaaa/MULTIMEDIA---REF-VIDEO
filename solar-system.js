(function () {
  var orbitalPeriods = {
    mercury: 0.2408467,
    venus: 0.61519726,
    earth: 1.0,
    mars: 1.8808158,
    jupiter: 11.862615,
    saturn: 29.447498,
    uranus: 84.016846,
    neptune: 164.79132,
    pluto: 248.0,
  };

  function capitalize(word) {
    return word.charAt(0).toUpperCase() + word.slice(1);
  }

  function formatYears(y) {
    if (y >= 1000000) return (y / 1000000).toFixed(2) + " million years";
    if (y >= 1000) return (y / 1000).toFixed(2) + " thousand years";
    if (y >= 1) return y.toFixed(2) + " years";
    if (y >= 0.01) return y.toFixed(2) + " years";
    return y.toFixed(4) + " years";
  }

  function formatRevolutions(r) {
    if (r >= 1000000) return (r / 1000000).toFixed(2) + " million";
    if (r >= 1000) return (r / 1000).toFixed(2) + " thousand";
    return r.toFixed(2);
  }

  function calculatePlanetaryTime() {
    var input = document.getElementById("earthYearsInput");
    var earthYears = parseFloat(input.value);
    if (Number.isNaN(earthYears) || earthYears < 0) earthYears = 0;

    Object.keys(orbitalPeriods).forEach(function (bodyName) {
      var period = orbitalPeriods[bodyName];
      var planetYears = earthYears / period;
      var revolutions = earthYears / period;

      document.querySelectorAll('[data-body="' + bodyName + '"].age-display').forEach(function (el) {
        el.textContent = formatYears(planetYears);
      });

      document.querySelectorAll('[data-body="' + bodyName + '"].revolution-display').forEach(function (el) {
        el.textContent = formatRevolutions(revolutions);
      });

      document.querySelectorAll('.time-comparison[data-body="' + bodyName + '"] .time-comparison-text').forEach(function (el) {
        if (earthYears === 0) {
          el.textContent =
            "Enter a positive number of Earth years above to see how time and orbits scale for " +
            capitalize(bodyName) +
            ".";
        } else if (earthYears === 1) {
          el.textContent =
            "In 1 Earth year, " +
            capitalize(bodyName) +
            " completes about " +
            formatRevolutions(1 / period) +
            " orbit(s) (" +
            formatYears(1 / period) +
            " local years).";
        } else {
          el.textContent =
            "In " +
            earthYears +
            " Earth years, " +
            capitalize(bodyName) +
            " experiences about " +
            formatYears(planetYears) +
            " of its own orbital years.";
        }
      });
    });

    var btn = document.getElementById("calcButton");
    if (btn) {
      var original = btn.getAttribute("data-label") || btn.innerHTML;
      if (!btn.getAttribute("data-label")) btn.setAttribute("data-label", original);
      btn.innerHTML = '<span aria-hidden="true">✓</span> Calculated';
      btn.classList.add("is-done");
      setTimeout(function () {
        btn.innerHTML = btn.getAttribute("data-label");
        btn.classList.remove("is-done");
      }, 1600);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    var input = document.getElementById("earthYearsInput");
    var btn = document.getElementById("calcButton");
    if (btn) btn.addEventListener("click", calculatePlanetaryTime);
    if (input) {
      input.addEventListener("keypress", function (e) {
        if (e.key === "Enter") calculatePlanetaryTime();
      });
      calculatePlanetaryTime();
    }
  });
})();
