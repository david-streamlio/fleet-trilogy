/* @ds-bundle: {"format":3,"namespace":"OfficialLeaveAsDefaultDRUIDSDesignSystem_019df7","components":[],"sourceHashes":{"sidebar.js":"8b4b3818ef6c","theme.js":"1314e9014651"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.OfficialLeaveAsDefaultDRUIDSDesignSystem_019df7 = window.OfficialLeaveAsDefaultDRUIDSDesignSystem_019df7 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// sidebar.js
try { (() => {
/* DRUIDS sidebar — single source of truth, injected into <aside class="nav" data-pageid="..."> */
(function () {
  const NAV = [{
    h: 'Start here',
    items: [{
      id: 'index',
      href: 'index.html',
      label: 'Overview'
    }, {
      id: 'cheatsheet',
      href: 'cheatsheet.html',
      label: 'Quick reference'
    }]
  }, {
    h: 'Designing for Datadog',
    items: [{
      id: 'page-patterns',
      href: 'page-patterns.html',
      label: 'Page-level layouts'
    }, {
      id: 'status',
      href: 'status.html',
      label: 'Status & semantic color'
    }, {
      id: 'typography',
      href: 'typography.html',
      label: 'Typography usage'
    }, {
      id: 'tables',
      href: 'tables.html',
      label: 'Tables & data display'
    }, {
      id: 'iconography',
      href: 'iconography.html',
      label: 'Iconography'
    }, {
      id: 'empty-loading-error',
      href: 'empty-loading-error.html',
      label: 'Empty states'
    }, {
      id: 'forms',
      href: 'forms.html',
      label: 'Form patterns'
    }, {
      id: 'messaging',
      href: 'messaging.html',
      label: 'Messaging & feedback'
    }, {
      id: 'anti-patterns',
      href: 'anti-patterns.html',
      label: 'Anti-patterns'
    }]
  }, {
    h: 'Foundations',
    items: [{
      id: 'color',
      href: 'color.html',
      label: 'Color'
    }, {
      id: 'spacing',
      href: 'spacing.html',
      label: 'Spacing & density'
    }, {
      id: 'border-radius-shadow',
      href: 'border-radius-shadow.html',
      label: 'Border, radius & shadow'
    }]
  }, {
    h: 'Components',
    items: [{
      id: 'navbar',
      href: 'components/navbar.html',
      label: 'Navbar'
    }, {
      id: 'product-header',
      href: 'components/product-header.html',
      label: 'Product header'
    }]
  }, {
    h: 'Templates',
    items: [{
      id: 'app-shell',
      href: 'templates/app-shell.html',
      label: 'App shell'
    }]
  }, {
    h: 'Reference',
    items: [{
      id: 'recipes',
      href: 'recipes.html',
      label: 'Recipes'
    }, {
      id: 'screenshot-test',
      href: 'screenshot-test.html',
      label: 'Screenshot test'
    }]
  }];
  const aside = document.querySelector('aside.nav[data-pageid]');
  if (!aside) return;
  const pageId = aside.dataset.pageid;
  const SUBDIRS = ['components', 'templates'];
  const currentSubdir = SUBDIRS.find(d => location.pathname.includes('/' + d + '/'));
  const inSubdir = Boolean(currentSubdir);
  const prefix = inSubdir ? '../' : '';
  const brand = `
    <div class="nav-brand">
      <img src="${prefix}../assets/druids-avatar.png" alt="" class="nav-logo">
      <div class="name">DRUIDS<small>Datadog Design System</small></div>
    </div>
    <button class="theme-toggle" type="button" onclick="window.__druidsToggleTheme && window.__druidsToggleTheme()" aria-label="Toggle theme">
      <span class="lbl-light">Switch to dark</span><span class="lbl-dark">Switch to light</span>
    </button>`;
  const sections = NAV.map(sec => {
    const items = sec.items.map(it => {
      const targetSubdir = SUBDIRS.find(d => it.href.startsWith(d + '/'));
      let href;
      if (!inSubdir) {
        // At root: link as-is (root files and subdir/file both work relative to root)
        href = it.href;
      } else if (targetSubdir === currentSubdir) {
        // Same subdir: drop the subdir prefix
        href = it.href.slice(currentSubdir.length + 1);
      } else if (targetSubdir) {
        // Different subdir: hop up then back down
        href = '../' + it.href;
      } else {
        // Root file from a subdir: hop up
        href = '../' + it.href;
      }
      const cls = it.id === pageId ? ' class="active"' : '';
      return `<li><a href="${href}"${cls}>${it.label}</a></li>`;
    }).join('');
    return `<div class="nav-section"><h4>${sec.h}</h4><ul class="nav-list">${items}</ul></div>`;
  }).join('');
  aside.innerHTML = brand + sections;

  // Mobile drawer: inject hamburger + backdrop, wire open/close behavior.
  // CSS gates these to viewports ≤ 980px; at desktop widths they're hidden.
  const toggle = document.createElement('button');
  toggle.className = 'nav-toggle';
  toggle.type = 'button';
  toggle.setAttribute('aria-label', 'Open navigation');
  toggle.innerHTML = '<svg viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><line x1="2.5" y1="4" x2="13.5" y2="4"/><line x1="2.5" y1="8" x2="13.5" y2="8"/><line x1="2.5" y1="12" x2="13.5" y2="12"/></svg>';
  document.body.appendChild(toggle);
  const backdrop = document.createElement('div');
  backdrop.className = 'nav-backdrop';
  document.body.appendChild(backdrop);
  const closeDrawer = () => {
    aside.classList.remove('open');
    backdrop.classList.remove('open');
    toggle.setAttribute('aria-expanded', 'false');
  };
  const openDrawer = () => {
    aside.classList.add('open');
    backdrop.classList.add('open');
    toggle.setAttribute('aria-expanded', 'true');
  };
  toggle.addEventListener('click', () => {
    if (aside.classList.contains('open')) closeDrawer();else openDrawer();
  });
  backdrop.addEventListener('click', closeDrawer);
  aside.addEventListener('click', e => {
    // Close after clicking a link (navigation will follow)
    if (e.target.closest('a')) closeDrawer();
  });
  window.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeDrawer();
  });
  // Reset on resize back to desktop so the drawer isn't stuck "open".
  window.addEventListener('resize', () => {
    if (window.innerWidth > 980) closeDrawer();
  });
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "sidebar.js", error: String((e && e.message) || e) }); }

// theme.js
try { (() => {
/* Theme toggle + persistence. Loads early so dark mode applies before paint. */
(function () {
  try {
    var saved = localStorage.getItem('druids-theme');
    if (saved === 'dark') document.documentElement.classList.add('theme-dark');
  } catch (e) {}
  function setTheme(t) {
    document.documentElement.classList.toggle('theme-dark', t === 'dark');
    try {
      localStorage.setItem('druids-theme', t);
    } catch (e) {}
  }
  window.__druidsToggleTheme = function () {
    var dark = document.documentElement.classList.contains('theme-dark');
    setTheme(dark ? 'light' : 'dark');
  };
})();
})(); } catch (e) { __ds_ns.__errors.push({ path: "theme.js", error: String((e && e.message) || e) }); }

})();
