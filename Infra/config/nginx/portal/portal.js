// Rohan Homelab Application Launcher & SalesSkip SSO Experience
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

  function enhanceLoginPage() {
    const stage = document.getElementById('first-factor-stage') || document.getElementById('second-factor-stage');
    if (!stage) return;

    const cardContainer = stage.querySelector('.mx-auto.w-full');
    if (!cardContainer) return;

    // 1. Prepend Left Blue Hero Panel if not present
    if (!document.getElementById('salesskip-hero-panel')) {
      const heroPanel = document.createElement('div');
      heroPanel.id = 'salesskip-hero-panel';
      heroPanel.className = 'salesskip-hero-panel';
      heroPanel.innerHTML = `
        <div class="salesskip-star-icon">
          <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
            <g stroke="#ffffff" stroke-width="7" stroke-linecap="round">
              <line x1="32" y1="10" x2="32" y2="54"/>
              <line x1="10" y1="32" x2="54" y2="32"/>
              <line x1="16.4" y1="16.4" x2="47.6" y2="47.6"/>
              <line x1="47.6" y1="16.4" x2="16.4" y2="47.6"/>
            </g>
          </svg>
        </div>

        <div class="salesskip-hero-content">
          <h1 class="salesskip-hero-title">
            Hello<br/>SalesSkip! <span class="wave-emoji">👋</span>
          </h1>
          <p class="salesskip-hero-desc">
            Skip repetitive and manual sales-marketing tasks. Get highly productive through automation and save tons of time!
          </p>
        </div>

        <div class="salesskip-hero-footer">
          © 2022 SalesSkip. All rights reserved.
        </div>

        <!-- Concentric geometric curved wireframes in background -->
        <svg class="salesskip-geo-lines" viewBox="0 0 500 500" fill="none">
          <rect x="140" y="40" width="320" height="420" rx="42" transform="rotate(20 140 40)" stroke="rgba(255,255,255,0.14)" stroke-width="1.5"/>
          <rect x="175" y="70" width="300" height="390" rx="42" transform="rotate(24 175 70)" stroke="rgba(255,255,255,0.11)" stroke-width="1.5"/>
          <rect x="210" y="100" width="280" height="360" rx="42" transform="rotate(28 210 100)" stroke="rgba(255,255,255,0.08)" stroke-width="1.5"/>
          <rect x="245" y="130" width="260" height="330" rx="42" transform="rotate(32 245 130)" stroke="rgba(255,255,255,0.05)" stroke-width="1.5"/>
        </svg>
      `;
      cardContainer.insertBefore(heroPanel, cardContainer.firstChild);
    }

    // 2. Insert Right Panel Header above form
    const form = stage.querySelector('#form-login') || stage.querySelector('form');
    if (form && !document.getElementById('salesskip-right-header')) {
      const rightHeader = document.createElement('div');
      rightHeader.id = 'salesskip-right-header';
      rightHeader.innerHTML = `
        <div class="salesskip-right-brand">SalesSkip</div>
        <div class="salesskip-welcome-wrap">
          <h2 class="salesskip-welcome-title">Welcome Back!</h2>
          <p class="salesskip-welcome-sub">
            Don't have an account? <span class="salesskip-link" id="salesskip-create-btn">Create a new account now</span>, it's FREE! Takes less than a minute.
          </p>
        </div>
      `;
      form.parentNode.insertBefore(rightHeader, form);

      const createBtn = document.getElementById('salesskip-create-btn');
      if (createBtn) {
        createBtn.addEventListener('click', (e) => {
          e.preventDefault();
          window.location.href = 'https://user.rohan.run.place/';
        });
      }
    }

    // 3. Customize Primary Button Text to "Login Now"
    const signInBtn = stage.querySelector('#sign-in-button');
    if (signInBtn) {
      if (signInBtn.childNodes && signInBtn.childNodes.length > 0) {
        for (let i = 0; i < signInBtn.childNodes.length; i++) {
          if (signInBtn.childNodes[i].nodeType === Node.TEXT_NODE) {
            signInBtn.childNodes[i].nodeValue = 'Login Now';
            break;
          }
        }
      }
    }

    // 4. Insert Google Login Button & "Forget password? Click here"
    if (form && !document.getElementById('salesskip-footer-links')) {
      const footerLinks = document.createElement('div');
      footerLinks.id = 'salesskip-footer-links';
      footerLinks.innerHTML = `
        <button type="button" class="salesskip-google-btn" id="salesskip-google-btn">
          <svg class="salesskip-google-icon" viewBox="0 0 24 24">
            <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
            <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
            <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
            <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
          </svg>
          Login with Google
        </button>
        <div class="salesskip-forget-wrap">
          Forget password? <span class="salesskip-click-here" id="salesskip-forget-link">Click here</span>
        </div>
      `;
      form.parentNode.appendChild(footerLinks);

      const forgetLink = document.getElementById('salesskip-forget-link');
      if (forgetLink) {
        forgetLink.addEventListener('click', (e) => {
          e.preventDefault();
          const origReset = document.getElementById('reset-password-button');
          if (origReset) {
            origReset.click();
          } else {
            window.location.href = '/reset-password/step1';
          }
        });
      }

      const googleBtn = document.getElementById('salesskip-google-btn');
      if (googleBtn) {
        googleBtn.addEventListener('click', () => {
          const passkeyBtn = document.querySelector('button[id*="passkey"]');
          if (passkeyBtn) {
            passkeyBtn.click();
          } else {
            signInBtn?.click();
          }
        });
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
        // Run enhanceLoginPage if hero panel is not yet present
        if (!document.getElementById('salesskip-hero-panel')) {
          enhanceLoginPage();
        }

        // Only check session when authenticated stage arrives
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
