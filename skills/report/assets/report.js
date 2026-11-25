/* Light / dark theme: the choice is remembered; the first visit follows the system setting. */
(function () {
  var KEY = 'report-theme', root = document.documentElement;
  function apply(t) {
    root.setAttribute('data-theme', t);
    var b = document.getElementById('theme');
    if (b) { b.textContent = '◐ ' + (t === 'dark' ? 'Light' : 'Dark'); b.setAttribute('aria-label', 'Switch to ' + (t === 'dark' ? 'light' : 'dark') + ' theme'); }
  }
  var forced = (location.search.match(/[?&]theme=(light|dark)/) || [])[1];  // ?theme=dark - for links and screenshots
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  apply(forced || saved || (window.matchMedia && matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  document.addEventListener('DOMContentLoaded', function () {
    apply(root.getAttribute('data-theme'));
    var b = document.getElementById('theme');
    if (b) b.onclick = function () {
      var t = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      apply(t);
      try { localStorage.setItem(KEY, t); } catch (e) {}
    };
  });
})();
