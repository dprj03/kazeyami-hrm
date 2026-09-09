(function () {
  function tick() {
    const el = document.getElementById("liveClock");
    if (!el) return;
    el.textContent = new Date().toLocaleTimeString("en-SG", {
      hour12: false,
      timeZone: "Asia/Singapore",
    });
  }
  tick();
  setInterval(tick, 1000);

  if (!navigator.geolocation) return;
  document.querySelectorAll("[data-clock-form]").forEach(function (form) {
    form.addEventListener("submit", function () {
      // Best-effort pin. Never block the punch if geo is denied.
    });
    navigator.geolocation.getCurrentPosition(
      function (pos) {
        form.querySelectorAll(".lat-field").forEach(function (n) {
          n.value = pos.coords.latitude.toFixed(6);
        });
        form.querySelectorAll(".lng-field").forEach(function (n) {
          n.value = pos.coords.longitude.toFixed(6);
        });
      },
      function () {},
      { enableHighAccuracy: false, timeout: 2500, maximumAge: 60000 }
    );
  });
})();
