/* Live clock for attendance page */
(function(){
  const el = document.getElementById('live-clock');
  if(!el) return;
  function tick(){
    const now = new Date();
    el.textContent = now.toLocaleTimeString('en-SG', {hour:'2-digit', minute:'2-digit', second:'2-digit', hour12:false});
  }
  tick();
  setInterval(tick, 1000);
})();
