// Rohan Run Place - Unified SSO & Homelab Portal Experience
(function () {
  'use strict';

  const BRAND_NAME = 'Rohan Run Place';

  const BASE_APPS = [
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
      id: 'portainer',
      name: 'Portainer CE',
      url: 'https://portainer.rohan.run.place/',
      subdomain: 'portainer.rohan.run.place',
      category: 'Infrastructure',
      logo: '/portal/icons/portainer.svg',
      isAllowed: (u) => u.isAdmin || u.groups.includes('portainer')
    },
    {
      id: 'firewall',
      name: 'Firewall & Traffic Limiter',
      url: 'https://firewall.rohan.run.place/',
      subdomain: 'firewall.rohan.run.place',
      category: 'Infrastructure',
      logo: '/portal/icons/firewall.svg',
      isAllowed: (u) => u.isAdmin || u.groups.includes('firewall')
    },
    {
      id: 'status',
      name: 'System Status',
      url: 'https://status.rohan.run.place/',
      subdomain: 'status.rohan.run.place',
      category: 'Infrastructure',
      logo: '/portal/icons/status.svg',
      isAllowed: () => true
    },
    {
      id: 'internal',
      name: 'Internal Homelab Hub',
      url: 'https://internal.rohan.run.place/',
      subdomain: 'internal.rohan.run.place',
      category: 'Administration',
      logo: '/portal/icons/internal.svg',
      isAllowed: (u) => u.isAdmin || u.groups.includes('internal') || u.groups.includes('apps-all')
    },
    {
      id: 'goto',
      name: 'In-House DNS & Gotos',
      url: 'https://goto.rohan.run.place/gotos',
      subdomain: 'goto.rohan.run.place',
      category: 'Infrastructure',
      logo: '/portal/icons/goto.svg',
      isAllowed: (u) => u.isAdmin || u.groups.includes('goto') || u.groups.includes('apps-all')
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
      id: 'paperclip',
      name: 'Paperclip AI Orchestrator',
      url: 'https://paperclip.rohan.run.place/',
      subdomain: 'paperclip.rohan.run.place',
      category: 'AI Tools',
      logo: '/portal/icons/paperclip.svg',
      isAllowed: (u) => u.isAdmin || u.groups.includes('paperclip') || u.groups.includes('ai-dev-core') || u.groups.includes('apps-all')
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

  let APPS = [...BASE_APPS];

  async function loadDynamicApps() {
    try {
      const res = await fetch('/portal/api/apps', { credentials: 'same-origin' });
      if (res.ok) {
        const dynamicList = await res.json();
        if (Array.isArray(dynamicList) && dynamicList.length > 0) {
          const list = dynamicList
            .filter(g => g.keyword !== 'auth' && g.keyword !== 'go')
            .map(g => {
              const kw = g.keyword.toLowerCase();
              const existing = BASE_APPS.find(a => a.id === kw || a.subdomain?.startsWith(kw + '.'));
              let targetUrl = g.target_url || (existing ? existing.url : `https://${kw}.rohan.run.place/`);
              let sub = (targetUrl && targetUrl.includes('//')) ? targetUrl.split('/')[2].split(':')[0] : `${kw}.rohan.run.place`;
              
              let logo = (existing && existing.logo) ? existing.logo : `/portal/icons/${kw}.svg`;
              return {
                id: kw,
                name: existing ? existing.name : (g.title || kw.toUpperCase()),
                url: targetUrl,
                subdomain: sub,
                category: existing ? existing.category : (g.category || 'Infrastructure'),
                description: g.description || (existing ? existing.description : ''),
                logo: logo,
                isAllowed: (u) => {
                  if (u.isAdmin) return true;
                  if (u.groups.includes('apps-all')) return true;
                  if (u.groups.includes(kw)) return true;
                  if (existing && existing.isAllowed) return existing.isAllowed(u);
                  if (['koel', 'snappymail', 'mail', 'webmail', 'lldap', 'user', 'users', 'status'].includes(kw)) return true;
                  return false;
                }
              };
            });

          const seen = new Set(list.map(a => a.id));
          for (const base of BASE_APPS) {
            if (!seen.has(base.id)) {
              list.push(base);
            }
          }
          APPS = list;
          return;
        }
      }
    } catch (e) {
      console.warn("Could not load dynamic apps from /portal/api/apps:", e);
    }
    APPS = [...BASE_APPS];
  }

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

  // -------------------------------------------------------------------------
  // 1. ENHANCE LOGIN PAGE (Step 1)
  // -------------------------------------------------------------------------
  function enhanceLoginPage() {
    const stage = document.getElementById('first-factor-stage');
    if (!stage) return;

    const cardContainer = stage.querySelector('.mx-auto.w-full');
    if (!cardContainer) return;

    // Prepend Left Blue Hero Panel with Unsplash Backdrop
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
            Hello<br/>${BRAND_NAME}! <span class="wave-emoji">👋</span>
          </h1>
        </div>

        <div class="salesskip-hero-footer">
          © 2026 ${BRAND_NAME}. All rights reserved.
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

    // Insert Right Panel Header above form
    const form = stage.querySelector('#form-login') || stage.querySelector('form');
    if (form && !document.getElementById('salesskip-right-header')) {
      const rightHeader = document.createElement('div');
      rightHeader.id = 'salesskip-right-header';
      rightHeader.innerHTML = `
        <div class="salesskip-right-brand">${BRAND_NAME}</div>
        <div class="salesskip-welcome-wrap">
          <h2 class="salesskip-welcome-title">Welcome Back!</h2>
        </div>
      `;
      form.parentNode.insertBefore(rightHeader, form);
    }

    // Customize Primary Button Text to "Login Now"
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

    // Insert "Forget password? Click here"
    if (form && !document.getElementById('salesskip-footer-links')) {
      const footerLinks = document.createElement('div');
      footerLinks.id = 'salesskip-footer-links';
      footerLinks.innerHTML = `
        <div class="salesskip-forget-wrap">
          Forget password? <span class="salesskip-click-here" id="salesskip-forget-link">Click here</span>
        </div>
      `;
      form.parentNode.appendChild(footerLinks);

      const forgetLink = document.getElementById('salesskip-forget-link');
      if (forgetLink) {
        forgetLink.addEventListener('click', (e) => {
          e.preventDefault();
          window.location.href = '/reset-password/step1';
        });
      }
    }
  }

  // -------------------------------------------------------------------------
  // 2. ENHANCE FORGOT PASSWORD PAGE (Step 1: Enter Username)
  // -------------------------------------------------------------------------
  function enhanceResetPasswordStep1() {
    const stage = document.getElementById('reset-password-step1-stage');
    if (!stage) return;

    const cardContainer = stage.querySelector('.mx-auto.w-full');
    if (!cardContainer) return;

    // Prepend Left Hero Panel (Architectural Unsplash Backdrop)
    if (!document.getElementById('reset-hero-panel')) {
      const heroPanel = document.createElement('div');
      heroPanel.id = 'reset-hero-panel';
      heroPanel.className = 'salesskip-hero-panel reset-hero';
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
            Reset<br/>Password 🔐
          </h1>
          <p class="salesskip-hero-desc">
            Forgot your password? No problem. Enter your username or email address and we'll help you securely verify your identity.
          </p>
        </div>

        <div class="salesskip-hero-footer">
          © 2026 ${BRAND_NAME}. All rights reserved.
        </div>

        <!-- Concentric geometric curved wireframes in background -->
        <svg class="salesskip-geo-lines" viewBox="0 0 500 500" fill="none">
          <rect x="140" y="40" width="320" height="420" rx="42" transform="rotate(20 140 40)" stroke="rgba(255,255,255,0.14)" stroke-width="1.5"/>
          <rect x="175" y="70" width="300" height="390" rx="42" transform="rotate(24 175 70)" stroke="rgba(255,255,255,0.11)" stroke-width="1.5"/>
          <rect x="210" y="100" width="280" height="360" rx="42" transform="rotate(28 210 100)" stroke="rgba(255,255,255,0.08)" stroke-width="1.5"/>
        </svg>
      `;
      cardContainer.insertBefore(heroPanel, cardContainer.firstChild);
    }

    // Insert Right Header
    const form = stage.querySelector('#form-reset-password-username') || stage.querySelector('form');
    if (form && !document.getElementById('reset-step1-header')) {
      const rightHeader = document.createElement('div');
      rightHeader.id = 'reset-step1-header';
      rightHeader.innerHTML = `
        <div class="salesskip-right-brand">${BRAND_NAME}</div>
        <div class="salesskip-welcome-wrap">
          <h2 class="salesskip-welcome-title">Forgot Password?</h2>
          <p class="salesskip-welcome-sub">
            Enter your account username below to receive a secure identity verification link.
          </p>
        </div>
      `;
      form.parentNode.insertBefore(rightHeader, form);
    }

    // Customize Buttons
    const resetBtn = stage.querySelector('#reset-button');
    if (resetBtn) {
      for (let i = 0; i < resetBtn.childNodes.length; i++) {
        if (resetBtn.childNodes[i].nodeType === Node.TEXT_NODE) {
          resetBtn.childNodes[i].nodeValue = 'Send Reset Link';
          break;
        }
      }
    }

    const cancelBtn = stage.querySelector('#cancel-button');
    if (cancelBtn) {
      for (let i = 0; i < cancelBtn.childNodes.length; i++) {
        if (cancelBtn.childNodes[i].nodeType === Node.TEXT_NODE) {
          cancelBtn.childNodes[i].nodeValue = 'Back to Login';
          break;
        }
      }
      cancelBtn.addEventListener('click', (e) => {
        e.preventDefault();
        window.location.href = '/';
      });
    }
  }

  // -------------------------------------------------------------------------
  // 3. ENHANCE FORGOT PASSWORD PAGE (Step 2: Enter New Password)
  // -------------------------------------------------------------------------
  function enhanceResetPasswordStep2() {
    const stage = document.getElementById('reset-password-step2-stage');
    if (!stage) return;

    const cardContainer = stage.querySelector('.mx-auto.w-full');
    if (!cardContainer) return;

    if (!document.getElementById('reset-step2-hero-panel')) {
      const heroPanel = document.createElement('div');
      heroPanel.id = 'reset-step2-hero-panel';
      heroPanel.className = 'salesskip-hero-panel reset-hero';
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
            Set New<br/>Password 🔑
          </h1>
          <p class="salesskip-hero-desc">
            Choose a strong, unique password for your ${BRAND_NAME} account to keep your services secure.
          </p>
        </div>

        <div class="salesskip-hero-footer">
          © 2026 ${BRAND_NAME}. All rights reserved.
        </div>
      `;
      cardContainer.insertBefore(heroPanel, cardContainer.firstChild);
    }

    const form = stage.querySelector('#form-reset-password') || stage.querySelector('form');
    if (form && !document.getElementById('reset-step2-header')) {
      const rightHeader = document.createElement('div');
      rightHeader.id = 'reset-step2-header';
      rightHeader.innerHTML = `
        <div class="salesskip-right-brand">${BRAND_NAME}</div>
        <div class="salesskip-welcome-wrap">
          <h2 class="salesskip-welcome-title">Set New Password</h2>
          <p class="salesskip-welcome-sub">
            Please enter and confirm your new password below.
          </p>
        </div>
      `;
      form.parentNode.insertBefore(rightHeader, form);
    }

    const resetBtn = stage.querySelector('#reset-button');
    if (resetBtn) {
      for (let i = 0; i < resetBtn.childNodes.length; i++) {
        if (resetBtn.childNodes[i].nodeType === Node.TEXT_NODE) {
          resetBtn.childNodes[i].nodeValue = 'Update Password';
          break;
        }
      }
    }

    const cancelBtn = stage.querySelector('#cancel-button');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', (e) => {
        e.preventDefault();
        window.location.href = '/';
      });
    }
  }

  // -------------------------------------------------------------------------
  // 4. APPLICATION LAUNCHER (AUTHENTICATED)
  // -------------------------------------------------------------------------
  async function renderPortal(user) {
    await loadDynamicApps();
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
            <h1>${BRAND_NAME} Portal</h1>
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
            <button class="category-filter-btn" data-cat="Infrastructure">Infrastructure</button>
            <button class="category-filter-btn" data-cat="Development">Development</button>
            <button class="category-filter-btn" data-cat="AI Tools">AI Tools</button>
            <button class="category-filter-btn" data-cat="Communication">Mail</button>
            <button class="category-filter-btn" data-cat="Media">Media</button>
            <button class="category-filter-btn" data-cat="Identity">Identity</button>
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

  // -------------------------------------------------------------------------
  // 5. LIFECYCLE & MUTATION OBSERVER
  // -------------------------------------------------------------------------
  function dispatchEnhancement() {
    if (document.getElementById('first-factor-stage')) {
      enhanceLoginPage();
    } else if (document.getElementById('reset-password-step1-stage')) {
      enhanceResetPasswordStep1();
    } else if (document.getElementById('reset-password-step2-stage')) {
      enhanceResetPasswordStep2();
    }
  }

  async function start() {
    const user = await checkUserSession();
    if (user) {
      await renderPortal(user);
    } else {
      dispatchEnhancement();

      let isCheckingSession = false;
      const observer = new MutationObserver(async () => {
        dispatchEnhancement();

        const root = document.getElementById('root');
        if (root && root.querySelector('#authenticated-stage') && !isCheckingSession) {
          isCheckingSession = true;
          const u = await checkUserSession();
          isCheckingSession = false;
          if (u) {
            observer.disconnect();
            await renderPortal(u);
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
