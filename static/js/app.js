document.addEventListener('submit', function(e){
  const btn = e.target.querySelector('button[type=submit]');
  if(btn){ btn.dataset.label = btn.textContent; }
});
