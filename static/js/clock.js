/* Live clock for attendance panel */
(function () {
  const el = document.getElementById("live-clock");
  if (!el) return;
  function tick() {
    const now = new Date();
    const opts = { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false, timeZone: "Asia/Singapore" };
    el.textContent = now.toLocaleTimeString("en-GB", opts);
  }
  tick();
  setInterval(tick, 1000);
})();
