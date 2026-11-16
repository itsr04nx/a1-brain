// Rohan Homelab Application Launcher & SSO Experience
(function () {
  'use strict';

  const APPS = [
    {
      id: 'browser',
      name: 'Browser',
      url: 'https://browser.rohan.run.place/',
      subdomain: 'browser.rohan.run.place',
      category: 'Development',
      logo: '/portal/icons/browser.svg',
      isAllowed: (u) => u.isAdmin || u.groups.includes('apps-all') || u.groups.includes('ai-dev-core') || u.groups.includes('browser')
    },
    {
      id: 'koel',
      name: 'Koel Music',
      url: 'https://koel.rohan.run.place/',
      subdomain: 'koel.rohan.run.place',
      category: 'Media',
      logo: '/portal/icons/koel.svg',
      isAllowed: () => true
    },
    {
      id: 'openhands',
      name: 'OpenHands AI',
      url: 'https://openhands.rohan.run.place/',
      subdomain: 'openhands.rohan.run.place',
      category: 'AI Tools',
      logo: '/portal/icons/openhands.png',
      isAllowed: (u) => u.isAdmin || u.groups.includes('ai-dev-core') || u.groups.includes('openhands')
    },
    {
      id: 'snappymail',
      name: 'SnappyMail',
      url: 'https://mail.rohan.run.place/',
      subdomain: 'mail.rohan.run.place',
      category: 'Communication',
      logo: '/portal/icons/snappymail.svg',
      isAllowed: () => true
    },
    {
      id: 'opencode',
      name: 'OpenCode IDE',
      url: 'https://opencode.rohan.run.place/',
      subdomain: 'opencode.rohan.run.place',
      category: 'Development',
      logo: '/portal/icons/opencode.png',
      isAllowed: (u) => u.isAdmin || u.groups.includes('ai-dev-core') || u.groups.includes('opencode')
    },
    {
      id: 'lldap',
      name: 'User Directory',
      url: 'https://user.rohan.run.place/',
      subdomain: 'user.rohan.run.place',
      category: 'Identity',
      logo: '/portal/icons/lldap.svg',
      isAllowed: () => true
    },
    {
      id: 'cockpit',
      name: 'Cockpit Console',
      url: 'https://cockpit.rohan.run.place/',
      subdomain: 'cockpit.rohan.run.place',
      category: 'Infrastructure',
      logo: '/portal/icons/cockpit.svg',
      isAllowed: (u) => u.isAdmin || u.groups.includes('cockpit')
    },
    {
      id: 'mailpit',
      name: 'Mailpit Testing',
      url: 'https://mailpit.rohan.run.place/',
      subdomain: 'mailpit.rohan.run.place',
      category: 'Developer',
      logo: '/portal/icons/mailpit.svg',
      isAllowed: (u) => u.isAdmin || u.groups.includes('mailpit')
    }
  ];

  async function checkUserSession() {
    try {
      const res = await fetch('/portal-user.json', { credentials: 'same-origin' });
      if (!res.ok) return null;
      const data = await res.json();
      if (!data.user) return null;
      const groupList = (data.groups || '').split(',').map((s) => s.trim().toLowerCase());
      const isAdmin = data.user === 'admin' || groupList.includes('admins') || groupList.includes('lldap_admin');
      return {
        username: data.user,
        name: data.name || data.user,
        email: data.email || `${data.user}@rohan.run.place`,
        groups: groupList,
        isAdmin: isAdmin
      };
    } catch (e) {
      return null;
    }
  }

  function getTargetServiceInfo() {
    const urlParams = new URLSearchParams(window.location.search);
    const rd = urlParams.get('rd') || '';
    const rdLower = rd.toLowerCase();

    if (rdLower.includes('browser.')) {
      return {
        name: 'Browser Session',
        badge: 'browser.run.place',
        icon: '🌐',
        isSpecific: true,
        desc: 'Sign in to access your isolated browser workspace'
      };
    } else if (rdLower.includes('koel.')) {
      return {
        name: 'Koel Music Player',
        badge: 'koel.rohan.run.place',
        icon: '🎵',
        isSpecific: true,
        desc: 'Sign in to access your streaming music library'
      };
    } else if (rdLower.includes('openhands.')) {
      return {
        name: 'OpenHands AI Workspace',
        badge: 'openhands.rohan.run.place',
        icon: '🤖',
        isSpecific: true,
        desc: 'Sign in to access your autonomous AI agents'
      };
    } else if (rdLower.includes('opencode.')) {
      return {
        name: 'OpenCode Web IDE',
        badge: 'opencode.rohan.run.place',
        icon: '💻',
        isSpecific: true,
        desc: 'Sign in to access your cloud development environment'
      };
    } else if (rdLower.includes('mail.') || rdLower.includes('webmail.')) {
      return {
        name: 'SnappyMail Webmail',
        badge: 'mail.rohan.run.place',
        icon: '📬',
        isSpecific: true,
        desc: 'Sign in to access your email account'
      };
    } else if (rdLower.includes('cockpit.')) {
      return {
        name: 'Cockpit Console',
        badge: 'cockpit.rohan.run.place',
        icon: '🖥️',
        isSpecific: true,
        desc: 'Sign in to manage server infrastructure'
      };
    } else if (rdLower.includes('user.') || rdLower.includes('users.')) {
      return {
        name: 'User Directory',
        badge: 'user.rohan.run.place',
        icon: '👤',
        isSpecific: true,
        desc: 'Sign in to manage account settings and passwords'
      };
    }

    return {
      name: 'Rohan Homelab SSO',
      badge: 'auth.rohan.run.place',
      icon: '✨',
      isSpecific: false,
      desc: 'Enter your credentials to unlock all homelab services'
    };
  }

  function enhanceLoginPage() {
    const stage = document.getElementById('first-factor-stage') || document.getElementById('second-factor-stage');
    if (!stage) return;

    // Hide original logo and titles
    const defaultLogo = stage.querySelector('.w-full.p-2');
    if (defaultLogo) defaultLogo.style.display = 'none';

    const defaultTitle = stage.querySelector('h5')?.closest('.w-full');
    if (defaultTitle) defaultTitle.style.display = 'none';

    const defaultSubtitle = stage.querySelector('h6')?.closest('.w-full');
    if (defaultSubtitle) defaultSubtitle.style.display = 'none';

    const targetService = getTargetServiceInfo();

    // Inject Custom SSO Header if not already present
    if (!document.getElementById('sso-login-header')) {
      const header = document.createElement('div');
      header.id = 'sso-login-header';
      header.className = 'sso-login-header';
      header.innerHTML = `
        <div class="sso-brand-badge" title="Rohan Homelab Secure Single Sign-On">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            <path d="M9 12l2 2 4-4"/>
          </svg>
        </div>
        <h1 class="sso-main-title">Rohan Homelab</h1>
        <div class="sso-target-indicator ${targetService.isSpecific ? 'highlight' : ''}">
          <span class="sso-pulse-dot"></span>
          <span class="sso-target-label">${targetService.icon} ${escapeHtml(targetService.name)}</span>
        </div>
        <p class="sso-sub-caption">${escapeHtml(targetService.desc)}</p>
      `;

      const form = stage.querySelector('#form-login') || stage.querySelector('form') || stage.querySelector('.mt-2.py-2');
      if (form && form.parentNode) {
        form.parentNode.insertBefore(header, form);
      }
    }

    // Inject Custom SSO Footer if not already present
    if (!document.getElementById('sso-login-footer')) {
      const footer = document.createElement('div');
      footer.id = 'sso-login-footer';
      footer.className = 'sso-login-footer';
      const urlParams = new URLSearchParams(window.location.search);
      const rdLower = (urlParams.get('rd') || '').toLowerCase();

      footer.innerHTML = `
        <div class="sso-services-pills">
          <span class="sso-pill ${rdLower.includes('browser') ? 'active' : ''}">🌐 Browser</span>
          <span class="sso-pill ${rdLower.includes('koel') ? 'active' : ''}">🎵 Koel</span>
          <span class="sso-pill ${rdLower.includes('openhands') ? 'active' : ''}">🤖 AI</span>
          <span class="sso-pill ${rdLower.includes('mail') ? 'active' : ''}">📬 Mail</span>
          <span class="sso-pill ${rdLower.includes('opencode') ? 'active' : ''}">💻 IDE</span>
        </div>
        <div class="sso-security-badge">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
            <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
          </svg>
          <span>End-to-End Encrypted Session • Rohan Homelab</span>
        </div>
      `;

      const form = stage.querySelector('#form-login') || stage.querySelector('form') || stage.querySelector('.mt-2.py-2');
      if (form && form.parentNode) {
        form.parentNode.appendChild(footer);
      }
    }
  }

  function renderPortal(user) {
    const root = document.getElementById('root');
    if (root) {
      root.style.display = 'none';
    }

    let existing = document.getElementById('rohan-homelab-portal');
    if (existing) {
      existing.remove();
    }

    const allowedApps = APPS.filter((app) => app.isAllowed(user));
    const portal = document.createElement('div');
    portal.id = 'rohan-homelab-portal';

    const avatarLetter = (user.name || user.username || 'U')[0].toUpperCase();
    const roleBadgeClass = user.isAdmin ? 'role-admin' : 'role-user';
    const roleTitle = user.isAdmin ? 'Administrator' : 'Standard User';

    portal.innerHTML = `
      <nav class="portal-navbar">
        <div class="portal-brand">
          <div class="portal-brand-logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div class="portal-brand-text">
            <h1>Homelab Portal</h1>
            <p><span class="status-dot-pulse"></span> SSO Active</p>
          </div>
        </div>

        <div class="portal-user-section">
          <div class="user-badge-card" title="${escapeHtml(user.email)}">
            <div class="user-avatar-bubble ${roleBadgeClass}">${avatarLetter}</div>
            <div class="user-info-text">
              <span class="user-display-name">${escapeHtml(user.name)}</span>
              <span class="user-role-label">${escapeHtml(roleTitle)}</span>
            </div>
          </div>
          <button class="btn-signout" id="portal-logout-btn" title="Sign out of SSO">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/>
              <line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Sign Out
          </button>
        </div>
      </nav>

      <main class="portal-content">
        <div class="portal-controls">
          <div class="portal-search-box">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <input type="text" id="portal-search-input" class="portal-search-input" placeholder="Search applications..." autocomplete="off" />
          </div>
          <div class="category-filter-group" id="portal-category-filters">
            <button class="category-filter-btn active" data-cat="all">All (${allowedApps.length})</button>
            <button class="category-filter-btn" data-cat="Development">Browser & IDE</button>
            <button class="category-filter-btn" data-cat="Media">Media</button>
            <button class="category-filter-btn" data-cat="AI Tools">AI</button>
            <button class="category-filter-btn" data-cat="Communication">Mail</button>
            <button class="category-filter-btn" data-cat="Identity">Identity</button>
            ${user.isAdmin ? '<button class="category-filter-btn" data-cat="Infrastructure">Admin</button>' : ''}
          </div>
        </div>

        <div class="portal-app-grid" id="portal-app-grid">
          ${allowedApps.map((app) => renderCardHtml(app)).join('')}
        </div>
      </main>
    `;

    document.body.appendChild(portal);

    // Logout action
    document.getElementById('portal-logout-btn').addEventListener('click', async () => {
      try {
        await fetch('/api/logout', { method: 'POST', credentials: 'same-origin' });
      } catch (e) {}
      window.location.reload();
    });

    // Search and filter handling
    const searchInput = document.getElementById('portal-search-input');
    const filterButtons = document.querySelectorAll('.category-filter-btn');
    let activeCategory = 'all';

    function applyFilters() {
      const query = (searchInput.value || '').toLowerCase().trim();
      const cards = document.querySelectorAll('.app-card');
      let visibleCount = 0;

      cards.forEach((card) => {
        const text = (card.dataset.searchText || '').toLowerCase();
        const category = card.dataset.category;
        const matchesQuery = !query || text.includes(query);
        const matchesCategory = activeCategory === 'all' || category === activeCategory;

        if (matchesQuery && matchesCategory) {
          card.style.display = 'flex';
          visibleCount++;
        } else {
          card.style.display = 'none';
        }
      });

      let emptyEl = document.getElementById('portal-empty-message');
      if (visibleCount === 0) {
        if (!emptyEl) {
          emptyEl = document.createElement('div');
          emptyEl.id = 'portal-empty-message';
          emptyEl.className = 'portal-empty-search';
          emptyEl.innerHTML = `<h3>No applications found</h3><p>Try searching for a different keyword or select "All".</p>`;
          document.getElementById('portal-app-grid').appendChild(emptyEl);
        }
      } else if (emptyEl) {
        emptyEl.remove();
      }
    }

    searchInput.addEventListener('input', applyFilters);

    filterButtons.forEach((btn) => {
      btn.addEventListener('click', () => {
        filterButtons.forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        activeCategory = btn.dataset.cat;
        applyFilters();
      });
    });
  }

  function renderCardHtml(app) {
    const searchText = `${app.name} ${app.category} ${app.subdomain}`;
    return `
      <a class="app-card" href="${escapeHtml(app.url)}" target="_blank" rel="noopener noreferrer" data-category="${escapeHtml(app.category)}" data-search-text="${escapeHtml(searchText)}" title="Open ${escapeHtml(app.name)}">
        <div class="app-icon-wrapper">
          <img class="app-real-logo" src="${escapeHtml(app.logo)}" alt="${escapeHtml(app.name)} logo" loading="lazy" onerror="this.onerror=null;this.src='/portal/icons/lldap.svg';" />
        </div>
        <div class="app-meta">
          <h2 class="app-name">${escapeHtml(app.name)}</h2>
        </div>
      </a>
    `;
  }

  function escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Session check and dynamic page initialization
  async function start() {
    const user = await checkUserSession();
    if (user) {
      renderPortal(user);
    } else {
      // Unauthenticated: Enhance the Login stage
      enhanceLoginPage();

      // Observe DOM with throttled session check
      let isCheckingSession = false;
      const observer = new MutationObserver(async () => {
        // Only run enhanceLoginPage if header is not yet present
        if (!document.getElementById('sso-login-header')) {
          enhanceLoginPage();
        }

        // Only check session when authenticated view arrives
        const root = document.getElementById('root');
        if (root && root.querySelector('#authenticated-stage') && !isCheckingSession) {
          isCheckingSession = true;
          const u = await checkUserSession();
          isCheckingSession = false;
          if (u) {
            observer.disconnect();
            renderPortal(u);
          }
        }
      });

      const root = document.getElementById('root') || document.body;
      if (root) {
        observer.observe(root, { childList: true, subtree: true });
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();
