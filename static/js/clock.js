function updateClock() {
  const el = document.getElementById('live-clock');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleTimeString('en-SG', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
}
document.addEventListener('DOMContentLoaded', () => {
  updateClock();
  setInterval(updateClock, 1000);
});
