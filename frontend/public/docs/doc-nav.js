/**
 * Shared navigation dropdown for HTML docs.
 * Include via <script src="doc-nav.js"></script> at end of <body>.
 * Automatically detects current page and highlights it.
 */
(function () {
  var docs = [
    { label: 'MRD', path: 'mrd.html' },
    { label: 'PRD', path: 'prd.html' },
    { label: 'Tech Spec', path: 'tech-spec.html' },
    { label: 'Test Plan', path: 'test-plan.html' },
    { label: 'Scalability', path: 'scalability.html' },
    { label: 'Security Review', path: 'security-review.html' },
    { label: 'Accessibility VPAT', path: 'accessibility-vpat.html' },
    { label: 'API vs DB Benchmark', path: 'api-vs-db-benchmark.html' },
  ];

  var currentFile = window.location.pathname.split('/').pop();
  var theme = new URLSearchParams(window.location.search).get('theme');
  var themeParam = theme ? '?theme=' + theme : '';
  var isDark = document.documentElement.classList.contains('dark-mode');

  // Create floating nav
  var nav = document.createElement('div');
  nav.style.cssText = 'position:fixed;top:12px;right:12px;z-index:9999;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:13px;';

  var btn = document.createElement('button');
  btn.textContent = 'Documents ▾';
  btn.style.cssText = 'padding:6px 14px;border-radius:6px;border:1px solid ' + (isDark ? '#3a4060' : '#d1d5db') + ';background:' + (isDark ? '#1a1d27' : '#fff') + ';color:' + (isDark ? '#c9cfe0' : '#374151') + ';cursor:pointer;font-size:13px;font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,0.1);';

  var dropdown = document.createElement('div');
  dropdown.style.cssText = 'display:none;position:absolute;right:0;top:100%;margin-top:4px;min-width:200px;border-radius:8px;border:1px solid ' + (isDark ? '#3a4060' : '#e2e6ef') + ';background:' + (isDark ? '#1a1d27' : '#fff') + ';box-shadow:0 4px 12px rgba(0,0,0,0.15);padding:4px 0;';

  docs.forEach(function (doc) {
    var a = document.createElement('a');
    a.href = doc.path + themeParam;
    a.textContent = doc.label;
    var isCurrent = currentFile === doc.path;
    a.style.cssText = 'display:block;padding:7px 14px;text-decoration:none;color:' + (isDark ? '#c9cfe0' : '#374151') + ';font-size:13px;' + (isCurrent ? 'font-weight:700;background:' + (isDark ? 'rgba(99,102,241,0.15)' : 'rgba(99,102,241,0.08)') + ';color:' + (isDark ? '#a5b4fc' : '#4f46e5') + ';' : '');
    a.onmouseenter = function () { if (!isCurrent) a.style.background = isDark ? '#252d45' : '#f3f4f6'; };
    a.onmouseleave = function () { if (!isCurrent) a.style.background = 'transparent'; };
    dropdown.appendChild(a);
  });

  // Add "Back to App" link
  var sep = document.createElement('div');
  sep.style.cssText = 'height:1px;background:' + (isDark ? '#3a4060' : '#e2e6ef') + ';margin:4px 0;';
  dropdown.appendChild(sep);
  var backLink = document.createElement('a');
  backLink.href = '/';
  backLink.textContent = '← Back to App';
  backLink.style.cssText = 'display:block;padding:7px 14px;text-decoration:none;color:' + (isDark ? '#94a0b8' : '#6b7280') + ';font-size:12px;';
  backLink.onmouseenter = function () { backLink.style.background = isDark ? '#252d45' : '#f3f4f6'; };
  backLink.onmouseleave = function () { backLink.style.background = 'transparent'; };
  dropdown.appendChild(backLink);

  btn.onclick = function (e) {
    e.stopPropagation();
    dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
  };
  document.addEventListener('click', function () { dropdown.style.display = 'none'; });

  nav.appendChild(btn);
  nav.appendChild(dropdown);
  document.body.appendChild(nav);
})();
