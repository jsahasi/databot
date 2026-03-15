/**
 * Shared navigation + theme toggle for HTML docs.
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
  var params = new URLSearchParams(window.location.search);
  var theme = params.get('theme');
  var isDark = document.documentElement.classList.contains('dark-mode');
  var themeParam = isDark ? '?theme=dark' : '';

  // Container — holds toggle + documents button
  var bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;top:12px;right:12px;z-index:9999;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:13px;display:flex;align-items:center;gap:8px;';

  // --- Theme pill toggle ---
  var pill = document.createElement('button');
  pill.setAttribute('aria-label', 'Toggle dark mode');
  pill.style.cssText = 'position:relative;width:44px;height:24px;border-radius:12px;border:1px solid ' + (isDark ? '#3a4060' : '#d1d5db') + ';background:' + (isDark ? '#2a2d3a' : '#e2e6ef') + ';cursor:pointer;padding:0;outline:none;transition:background 0.2s;box-shadow:0 1px 3px rgba(0,0,0,0.1);';

  var knob = document.createElement('span');
  knob.style.cssText = 'position:absolute;top:2px;' + (isDark ? 'left:22px' : 'left:2px') + ';width:18px;height:18px;border-radius:50%;background:' + (isDark ? '#a5b4fc' : '#fff') + ';transition:left 0.2s;box-shadow:0 1px 2px rgba(0,0,0,0.2);';

  var icon = document.createElement('span');
  icon.textContent = isDark ? '\u263E' : '\u2600';
  icon.style.cssText = 'position:absolute;top:2px;font-size:12px;line-height:18px;' + (isDark ? 'left:4px;color:#7c8499;' : 'right:4px;color:#d97706;');

  pill.appendChild(icon);
  pill.appendChild(knob);

  pill.onclick = function (e) {
    e.stopPropagation();
    var base = window.location.pathname;
    var newTheme = isDark ? 'light' : 'dark';
    window.location.href = base + '?theme=' + newTheme;
  };

  // --- Documents button + dropdown ---
  var btnWrap = document.createElement('div');
  btnWrap.style.cssText = 'position:relative;';

  var btn = document.createElement('button');
  btn.textContent = 'Documents \u25BE';
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

  // Separator + Back to App
  var sep = document.createElement('div');
  sep.style.cssText = 'height:1px;background:' + (isDark ? '#3a4060' : '#e2e6ef') + ';margin:4px 0;';
  dropdown.appendChild(sep);
  var backLink = document.createElement('a');
  backLink.href = '/';
  backLink.textContent = '\u2190 Back to App';
  backLink.style.cssText = 'display:block;padding:7px 14px;text-decoration:none;color:' + (isDark ? '#94a0b8' : '#6b7280') + ';font-size:12px;';
  backLink.onmouseenter = function () { backLink.style.background = isDark ? '#252d45' : '#f3f4f6'; };
  backLink.onmouseleave = function () { backLink.style.background = 'transparent'; };
  dropdown.appendChild(backLink);

  btn.onclick = function (e) {
    e.stopPropagation();
    dropdown.style.display = dropdown.style.display === 'none' ? 'block' : 'none';
  };
  document.addEventListener('click', function () { dropdown.style.display = 'none'; });

  btnWrap.appendChild(btn);
  btnWrap.appendChild(dropdown);

  // Assemble: [pill toggle] [Documents ▾]
  bar.appendChild(pill);
  bar.appendChild(btnWrap);
  document.body.appendChild(bar);

  // Remove any standalone #theme-toggle elements (legacy)
  var legacy = document.getElementById('theme-toggle');
  if (legacy) legacy.parentNode.removeChild(legacy);
})();
