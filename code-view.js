(function () {
  var allowedScripts = {
    "Sun.py": true,
    "Mercury.py": true,
    "Venus.py": true,
    "Earth.py": true,
    "Mars.py": true,
    "Jupiter.py": true,
    "Saturn.py": true,
    "Uranus.py": true,
    "Neptune.py": true,
    "Pluto.py": true,
    "final_render.py": true,
  };

  var scriptBase = "blender%20files/";

  function getScriptName() {
    var params = new URLSearchParams(window.location.search);
    return params.get("script") || "";
  }

  function setError(message) {
    var lede = document.getElementById("code-lede");
    var panel = document.getElementById("code-panel");
    var content = document.getElementById("code-content");
    if (lede) lede.textContent = message;
    if (panel) panel.classList.add("is-error");
    if (content) content.textContent = message;
  }

  document.addEventListener("DOMContentLoaded", function () {
    var script = getScriptName();
    var title = document.getElementById("code-title");
    var lede = document.getElementById("code-lede");
    var content = document.getElementById("code-content");
    var download = document.getElementById("code-download");

    if (!script || !allowedScripts[script]) {
      if (title) title.textContent = "Script not found";
      setError("Choose a valid script from the solar system page.");
      return;
    }

    document.title = script + " | Multimedia Portfolio";
    if (title) title.textContent = script;
    if (lede) lede.textContent = "Read-only view of the Blender Python script.";

    var fileUrl = scriptBase + encodeURIComponent(script);

    if (download) {
      download.href = fileUrl;
      download.download = script;
      download.hidden = false;
    }

    fetch(fileUrl)
      .then(function (response) {
        if (!response.ok) throw new Error("Could not load " + script + ".");
        return response.text();
      })
      .then(function (text) {
        if (content) content.textContent = text;
        if (lede) lede.textContent = "Read-only view — use Download on the solar system page to save this file.";
      })
      .catch(function () {
        setError("Could not load " + script + ". Make sure the file exists in blender files/.");
      });
  });
})();
