document.addEventListener('DOMContentLoaded', () => {
  // flash auto-dismiss
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => el.classList.add('fade-out'), 4000);
  });
});
