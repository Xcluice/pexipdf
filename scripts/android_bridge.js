
// ─── ANDROID APP SHELL · PRO PDF VIEWER · DEVICE PDF LIST · NATIVE BRIDGE ────
(function () {
  const tabs = ['home', 'viewer', 'tools', 'settings'];
  let activeTab = 'home';

  const THEME_SVGS = {
    orig: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>',
    night: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>',
    sepia: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>'
  };


  const TOAST_SVGS = {
    info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>',
    success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>',
    error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
  };
  let _toastTimer = null;
  window.showToast = function (msg, duration, type) {
    const t = document.getElementById('toast');
    if (!t) return;
    const ico = document.getElementById('toast-ico');
    const txt = document.getElementById('toast-msg');
    const low = String(msg || '').toLowerCase();
    const kind = type || (/(fail|error|could not|unable|denied|incorrect|needed|required)/.test(low) ? 'error' : (/(saved|copied|added|captured|up to date|resumed)/.test(low) ? 'success' : 'info'));
    if (ico) ico.innerHTML = TOAST_SVGS[kind] || TOAST_SVGS.info;
    if (txt) txt.textContent = String(msg || '');
    else t.textContent = String(msg || '');
    t.className = 'show toast-' + kind;
    clearTimeout(_toastTimer);
    _toastTimer = setTimeout(() => { t.classList.remove('show'); }, duration || 2400);
  };

  const bnavInd = document.getElementById('bnav-indicator');
  function moveNavPill(idx, animate) {
    if (!bnavInd) return;
    if (!animate) bnavInd.style.transition = 'none';
    bnavInd.style.transform = `translate3d(${idx * 100}%, 0, 0)`;
    if (!animate) {
      void bnavInd.offsetWidth;
      bnavInd.style.transition = '';
    }
  }

  function switchTab(tab, opts) {
    if (!tabs.includes(tab)) return;
    const prevIdx = tabs.indexOf(activeTab);
    const nextIdx = tabs.indexOf(tab);
    const dirClass = nextIdx >= prevIdx ? 'tg-from-right' : 'tg-from-left';
    activeTab = tab;
    moveNavPill(nextIdx, prevIdx !== nextIdx);

    document.querySelectorAll('.app-screen').forEach(s => {
      const on = s.dataset.screen === tab;
      s.classList.remove('tg-from-right', 'tg-from-left');
      s.classList.toggle('active', on);
      if (on) {
        s.style.animation = 'none';
        void s.offsetWidth;
        s.style.animation = '';
        s.classList.add(dirClass);
      }
    });
    document.querySelectorAll('.bnav-item').forEach(b => {
      const on = b.dataset.tab === tab;
      b.classList.toggle('active', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
    document.body.classList.toggle('viewer-mode', tab === 'viewer');
    if (tab === 'viewer' && window.PexiBridge && window.PexiBridge.listDevicePdfs && !PV.doc) {
      refreshDevicePdfs();
    }
    const scrollEl = document.getElementById('app-scroll');
    if (scrollEl && !(opts && opts.keepScroll)) scrollEl.scrollTop = 0;
  }
  moveNavPill(0, false);


  window.__pexiSwitchTab = switchTab;

  document.querySelectorAll('.bnav-item').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  window.__pexiSyncPages = function (n) {
    const topPill = document.getElementById('top-pages-pill');
    const topPillNum = document.getElementById('top-pages-num');
    if (topPill && topPillNum) {
      topPillNum.textContent = n + (n === 1 ? ' page' : ' pages');
      topPill.style.display = n > 0 ? 'inline-flex' : 'none';
    }
    const lastBtn = document.getElementById('pv-open-last');
    if (lastBtn) lastBtn.style.display = (typeof lastPdfBlob !== 'undefined' && lastPdfBlob) ? 'inline-flex' : 'none';
  };

  document.getElementById('top-pages-pill')?.addEventListener('click', () => {
    switchTab('home', { keepScroll: true });
    const sec = document.getElementById('preview-section');
    if (sec && sec.style.display !== 'none') sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
  document.getElementById('pages-add-btn')?.addEventListener('click', () => document.getElementById('file-input').click());

  window.__pexiAddCapturedPhoto = function (base64, name, size) {
    try {
      const bin = atob(base64);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      const blob = new Blob([bytes], { type: 'image/jpeg' });
      images.push({
        file: blob,
        url: URL.createObjectURL(blob),
        name: name || ('scan_' + Date.now() + '.jpg'),
        size: size || blob.size,
        rotation: 0,
        selected: false
      });
      renderGrid();
      switchTab('home', { keepScroll: true });
      setTimeout(() => document.getElementById('preview-section')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 150);
      showToast('Photo added');
    } catch (e) {
      console.error(e);
      showToast('Could not import captured photo');
    }
  };

  document.querySelectorAll('[data-trigger]').forEach(el => {
    el.addEventListener('click', () => {
      const target = document.getElementById(el.dataset.trigger);
      if (target) target.click();
    });
  });

  const settingsDark = document.getElementById('settings-dark-toggle');
  if (settingsDark) {
    settingsDark.checked = document.documentElement.classList.contains('dark');
    settingsDark.addEventListener('change', () => setTheme(settingsDark.checked));
  }

  const aboutModal = document.getElementById('about-modal');
  const openAbout = () => { if (aboutModal) aboutModal.style.display = 'flex'; };
  const closeAbout = () => { if (aboutModal) aboutModal.style.display = 'none'; };
  document.getElementById('about-btn')?.addEventListener('click', openAbout);
  document.getElementById('settings-about-row')?.addEventListener('click', openAbout);
  document.getElementById('about-close-btn')?.addEventListener('click', closeAbout);

  document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', e => {
      if (e.target !== overlay) return;
      if (overlay.id === 'camera-modal') document.getElementById('cam-close-btn')?.click();
      else if (overlay.id === 'text-modal') document.getElementById('text-cancel-btn')?.click();
      else if (overlay.id === 'crop-modal') document.getElementById('crop-cancel-btn')?.click();
      else if (overlay.id === 'name-modal') document.getElementById('name-cancel-btn')?.click();
      else if (overlay.id === 'compress-modal') document.getElementById('compress-close-btn')?.click();
      else if (overlay.id === 'compress-video-modal') document.getElementById('compress-video-close-btn')?.click();
      else if (overlay.id === 'gt-modal') document.getElementById('gt-close')?.click();
      else if (overlay.id === 'about-modal') closeAbout();
      else if (overlay.id === 'pv-jump-modal') overlay.classList.remove('open');
      else if (overlay.id === 'pv-pass-modal') { document.getElementById('pv-pass-cancel')?.click(); }
    });
  });

  let devicePdfs = [];
  const pvDevSection = document.getElementById('pv-device-section');
  const pvDevList = document.getElementById('pv-device-list');
  const pvDevCount = document.getElementById('pv-device-count');
  const pvDevFilter = document.getElementById('pv-device-filter');
  const pvPermCard = document.getElementById('pv-perm-card');

  function fmtRelDate(sec) {
    if (!sec) return '';
    const diff = Math.max(0, Math.floor(Date.now() / 1000) - sec);
    if (diff < 3600) return Math.max(1, Math.floor(diff / 60)) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
    const d = new Date(sec * 1000);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  function escHtml(s) {
    return String(s || '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  const pdfThumbCache = new Map();
  const pdfThumbRequested = new Set();
  let pdfThumbIO = null;
  let pvViewMode = localStorage.getItem('pexi_pv_view') || 'list';
  let pvSortMode = localStorage.getItem('pexi_pv_sort') || 'recent';
  const pvViewBtn = document.getElementById('pv-view-btn');
  const pvSortBtn = document.getElementById('pv-sort-btn');

  function getReadPositions() {
    try { return JSON.parse(localStorage.getItem('pexi_read_pos') || '{}') || {}; } catch (_) { return {}; }
  }
  function saveReadPosition(name, size, page, total) {
    if (!name || !page || page < 1) return;
    try {
      const map = getReadPositions();
      const k = name.toLowerCase() + '_' + (size || 0);
      map[k] = { page, total: total || 0, ts: Date.now() };
      const keys = Object.keys(map);
      if (keys.length > 80) {
        keys.sort((a, b) => (map[a].ts || 0) - (map[b].ts || 0)).slice(0, keys.length - 80).forEach(dk => delete map[dk]);
      }
      localStorage.setItem('pexi_read_pos', JSON.stringify(map));
    } catch (_) {}
  }
  function getSavedPage(name, size) {
    const map = getReadPositions();
    const hit = map[(name || '').toLowerCase() + '_' + (size || 0)];
    return hit && hit.page > 1 ? hit.page : 0;
  }

  function pdfItemKey(p) {
    return `${(p.name || '').toLowerCase()}_${p.size || 0}_${p.modified || 0}`;
  }

  function syncViewSortUi() {
    if (pvViewBtn) {
      pvViewBtn.innerHTML = pvViewMode === 'grid'
        ? '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>'
        : '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></svg>';
      pvViewBtn.title = pvViewMode === 'grid' ? 'Switch to list view' : 'Switch to grid view';
    }
    if (pvSortBtn) {
      const labels = { recent: 'Recent', name: 'A–Z', size: 'Size' };
      pvSortBtn.textContent = labels[pvSortMode] || 'Recent';
    }
  }
  syncViewSortUi();

  pvViewBtn?.addEventListener('click', () => {
    pvViewMode = pvViewMode === 'list' ? 'grid' : 'list';
    localStorage.setItem('pexi_pv_view', pvViewMode);
    syncViewSortUi();
    renderDevicePdfList();
  });
  pvSortBtn?.addEventListener('click', () => {
    const order = ['recent', 'name', 'size'];
    pvSortMode = order[(order.indexOf(pvSortMode) + 1) % order.length];
    localStorage.setItem('pexi_pv_sort', pvSortMode);
    syncViewSortUi();
    renderDevicePdfList();
  });

  function applyThumbToEl(el, cached) {
    if (!el || !cached) return;
    const frame = el.querySelector('.pv-dev-thumb');
    const pgEl = el.querySelector('.pv-dev-pg');
    if (cached.url && frame) {
      let img = frame.querySelector('img');
      if (!img) {
        img = document.createElement('img');
        img.alt = '';
        frame.appendChild(img);
      }
      if (img.src !== cached.url) img.src = cached.url;
      frame.classList.add('has-img');
    } else if (cached.pages === -2 && frame) {
      frame.classList.add('is-locked');
    }
    if (pgEl) {
      if (cached.pages > 0) {
        pgEl.textContent = `${cached.pages} pg`;
        pgEl.style.display = 'inline-flex';
      } else if (cached.pages === -2) {
        pgEl.textContent = 'Locked';
        pgEl.style.display = 'inline-flex';
      }
    }
  }

  window.__pexiOnPdfThumb = function (key, dataUrl, pageCount) {
    const rec = { url: dataUrl || '', pages: typeof pageCount === 'number' ? pageCount : 0 };
    pdfThumbCache.set(key, rec);
    if (!pvDevList) return;
    pvDevList.querySelectorAll('.pv-dev-row').forEach(el => {
      if (el.dataset.key === key) applyThumbToEl(el, rec);
    });
  };

  function renderDevicePdfList() {
    if (!pvDevList) return;
    if (pdfThumbIO) { pdfThumbIO.disconnect(); pdfThumbIO = null; }
    const q = (pvDevFilter?.value || '').trim().toLowerCase();
    let filtered = q ? devicePdfs.filter(p => (p.name || '').toLowerCase().includes(q) || (p.folder || '').toLowerCase().includes(q)) : devicePdfs.slice();
    if (pvSortMode === 'name') filtered.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    else if (pvSortMode === 'size') filtered.sort((a, b) => (b.size || 0) - (a.size || 0));
    else filtered.sort((a, b) => (b.modified || 0) - (a.modified || 0));

    pvDevList.classList.toggle('is-grid', pvViewMode === 'grid');
    if (pvDevCount) pvDevCount.textContent = filtered.length ? `${filtered.length} PDF${filtered.length === 1 ? '' : 's'}` : '';
    if (!filtered.length) {
      pvDevList.innerHTML = `<div class="pv-dev-empty">${q ? 'No matching PDFs found.' : 'No PDFs found on device yet. Allow storage access to scan your PDFs.'}</div>`;
      return;
    }
    const readPos = getReadPositions();
    pvDevList.innerHTML = filtered.map((p, idx) => {
      const key = pdfItemKey(p);
      const cached = pdfThumbCache.get(key);
      const saved = readPos[(p.name || '').toLowerCase() + '_' + (p.size || 0)];
      const resumeBadge = saved && saved.page > 1 ? `<span class="pv-dev-resume">Pg ${saved.page}</span>` : '';
      const pgText = cached && cached.pages > 0 ? `${cached.pages} pg` : (cached && cached.pages === -2 ? 'Locked' : '');
      return `
      <button type="button" class="pv-dev-row" data-idx="${idx}" data-key="${escHtml(key)}" data-uri="${escHtml(p.uri || '')}">
        <span class="pv-dev-thumb${cached && cached.url ? ' has-img' : ''}${cached && cached.pages === -2 ? ' is-locked' : ''}" aria-hidden="true">
          <svg class="pv-dev-fallback" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M9 15h6M9 11h3"/>
          </svg>
          ${cached && cached.url ? `<img src="${cached.url}" alt="">` : ''}
          <span class="pv-dev-pg" style="${pgText ? 'display:inline-flex;' : 'display:none;'}">${escHtml(pgText)}</span>
        </span>
        <span class="pv-dev-body">
          <span class="pv-dev-name">${escHtml(p.name)}</span>
          <span class="pv-dev-meta">${escHtml(formatBytes(p.size || 0))}${p.folder ? ' · ' + escHtml(p.folder) : ''}${p.modified ? ' · ' + fmtRelDate(p.modified) : ''}${resumeBadge}</span>
        </span>
        <span class="pv-dev-chev" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
        </span>
      </button>`;
    }).join('');

    const rows = pvDevList.querySelectorAll('.pv-dev-row');
    rows.forEach(btn => {
      btn.addEventListener('click', () => {
        const item = filtered[parseInt(btn.dataset.idx, 10)];
        if (item && window.PexiBridge && window.PexiBridge.openPdfUri) {
          window.PexiBridge.openPdfUri(item.uri);
        }
      });
    });

    if (window.PexiBridge && window.PexiBridge.requestPdfThumbnail) {
      pdfThumbIO = new IntersectionObserver(entries => {
        entries.forEach(en => {
          if (!en.isIntersecting) return;
          const el = en.target;
          const key = el.dataset.key;
          const uri = el.dataset.uri;
          pdfThumbIO.unobserve(el);
          if (!key || !uri) return;
          const cached = pdfThumbCache.get(key);
          if (cached) { applyThumbToEl(el, cached); return; }
          if (!pdfThumbRequested.has(key)) {
            pdfThumbRequested.add(key);
            try { window.PexiBridge.requestPdfThumbnail(uri, key); } catch (_) {}
          }
        });
      }, { rootMargin: '260px 0px' });
      rows.forEach(r => pdfThumbIO.observe(r));
    }
  }

  function refreshDevicePdfs() {
    if (!window.PexiBridge || !window.PexiBridge.listDevicePdfs) return;
    if (pvDevSection) pvDevSection.style.display = 'flex';
    if (pvDevList && !devicePdfs.length) {
      pvDevList.innerHTML = '<div class="pv-dev-empty">Scanning PDFs on device…</div>';
    }
    try { window.PexiBridge.listDevicePdfs(); } catch (_) {}
  }

  window.__pexiOnDevicePdfs = function (payload) {
    try {
      const data = typeof payload === 'string' ? JSON.parse(payload) : payload;
      devicePdfs = Array.isArray(data.items) ? data.items : [];
      if (pvDevSection) pvDevSection.style.display = 'flex';
      if (pvPermCard) pvPermCard.style.display = data.needsPermission ? 'flex' : 'none';
      renderDevicePdfList();
    } catch (e) {
      console.error(e);
    }
  };

  pvDevFilter?.addEventListener('input', renderDevicePdfList);
  document.getElementById('pv-refresh-btn')?.addEventListener('click', refreshDevicePdfs);
  document.getElementById('pv-perm-btn')?.addEventListener('click', () => {
    if (window.PexiBridge && window.PexiBridge.requestPdfListPermission) {
      window.PexiBridge.requestPdfListPermission();
    }
  });

  const PV = {
    doc: null,
    name: '',
    rawBytes: null,
    numPages: 0,
    curPage: 1,
    zoom: 1.0,
    rotation: 0,
    mode: 'scroll',
    theme: 'orig',
    rendered: new Set(),
    rendering: new Set(),
    io: null,
    textCache: new Map(),
    matches: [],
    matchIdx: -1,
    thumbsBuilt: false
  };

  const pvEmpty = document.getElementById('pv-empty');
  const pvStage = document.getElementById('pv-stage');
  const pvPages = document.getElementById('pv-pages');
  const pvTitle = document.getElementById('pv-title');
  const pvPagePill = document.getElementById('pv-page-pill');
  const pvProgFill = document.getElementById('pv-prog-fill');
  const pvZoomLabel = document.getElementById('pv-zoom-label');
  const pvSearchBar = document.getElementById('pv-search-bar');
  const pvSearchInput = document.getElementById('pv-search-input');
  const pvSearchCount = document.getElementById('pv-search-count');
  const pvThumbs = document.getElementById('pv-thumbs');
  const pvThemeBtn = document.getElementById('pv-theme-btn');
  const pvModeBtn = document.getElementById('pv-mode-btn');

  let _savePosTimer = null;
  function pvUpdateMeta() {
    if (!PV.numPages) return;
    pvPagePill.textContent = `${PV.curPage} / ${PV.numPages}`;
    pvProgFill.style.width = Math.round((PV.curPage / PV.numPages) * 100) + '%';
    pvZoomLabel.textContent = Math.round(PV.zoom * 100) + '%';
    if (pvThumbs.style.display && pvThumbs.style.display !== 'none') {
      pvThumbs.querySelectorAll('.pv-thumb').forEach(t => {
        t.classList.toggle('active', parseInt(t.dataset.p, 10) === PV.curPage);
      });
    }
    if (PV.name && PV.rawBytes) {
      clearTimeout(_savePosTimer);
      const nm = PV.name, sz = PV.rawBytes.length, cp = PV.curPage, np = PV.numPages;
      _savePosTimer = setTimeout(() => saveReadPosition(nm, sz, cp, np), 600);
    }
  }

  let _pvQueue = [];
  let _pvPumping = false;
  let _pvScrolling = false;
  let _pvScrollIdleTimer = null;
  let _pvRenderGen = 0;

  function pvPruneFarPages() {
    if (PV.mode !== 'scroll' || PV.rendered.size <= 9) return;
    const keepRadius = 4;
    for (const pNum of Array.from(PV.rendered)) {
      if (Math.abs(pNum - PV.curPage) > keepRadius) {
        const slot = pvPages.querySelector(`.pv-page[data-p="${pNum}"]`);
        if (slot) {
          const c = slot.querySelector('canvas');
          if (c) { c.width = 0; c.height = 0; }
          slot.innerHTML = `<div class="pv-skel">Page ${pNum}</div>`;
        }
        PV.rendered.delete(pNum);
      }
    }
  }

  function pvEnqueueRender(pNum) {
    if (!PV.doc || PV.rendered.has(pNum) || PV.rendering.has(pNum)) return;
    if (!_pvQueue.includes(pNum)) _pvQueue.push(pNum);
    if (!_pvScrolling) pvPumpQueue();
  }

  async function pvPumpQueue() {
    if (_pvPumping || !PV.doc) return;
    _pvPumping = true;
    const gen = _pvRenderGen;
    try {
      while (_pvQueue.length && PV.doc && gen === _pvRenderGen) {
        if (_pvScrolling) break;
        _pvQueue.sort((a, b) => Math.abs(a - PV.curPage) - Math.abs(b - PV.curPage));
        const pNum = _pvQueue.shift();
        if (pNum === undefined || PV.rendered.has(pNum) || PV.rendering.has(pNum)) continue;
        if (PV.mode === 'scroll' && Math.abs(pNum - PV.curPage) > 4) continue;
        await pvRenderPage(pNum, gen);
        // Yield a frame between pages so touch scrolling stays 60fps
        await new Promise(r => requestAnimationFrame(r));
      }
      if (gen === _pvRenderGen) pvPruneFarPages();
    } finally {
      _pvPumping = false;
    }
  }

  pvPages?.addEventListener('scroll', () => {
    _pvScrolling = true;
    clearTimeout(_pvScrollIdleTimer);
    _pvScrollIdleTimer = setTimeout(() => {
      _pvScrolling = false;
      pvPumpQueue();
    }, 90);
  }, { passive: true });

  async function pvRenderPage(pNum, gen) {
    if (!PV.doc || PV.rendered.has(pNum) || PV.rendering.has(pNum)) return;
    const slot = pvPages.querySelector(`.pv-page[data-p="${pNum}"]`);
    if (!slot) return;
    PV.rendering.add(pNum);
    try {
      const page = await PV.doc.getPage(pNum);
      if (gen !== undefined && gen !== _pvRenderGen) return;
      const rot = ((page.rotate || 0) + PV.rotation) % 360;
      const baseVp = page.getViewport({ scale: 1, rotation: rot });
      const availW = Math.max(260, pvPages.clientWidth - 16);
      const fitScale = availW / baseVp.width;
      const cssScale = fitScale * PV.zoom;
      const maxDpr = PV.zoom > 1.25 ? 1.75 : 1.45;
      const dpr = Math.min(window.devicePixelRatio || 1, maxDpr);
      const vp = page.getViewport({ scale: cssScale * dpr, rotation: rot });

      let canvas = slot.querySelector('canvas');
      if (!canvas) {
        canvas = document.createElement('canvas');
        slot.innerHTML = '';
        slot.appendChild(canvas);
        const badge = document.createElement('span');
        badge.className = 'pv-pnum';
        badge.textContent = String(pNum);
        slot.appendChild(badge);
      }
      canvas.width = Math.floor(vp.width);
      canvas.height = Math.floor(vp.height);
      const cssW = Math.floor(baseVp.width * cssScale);
      const cssH = Math.floor(baseVp.height * cssScale);
      canvas.style.width = cssW + 'px';
      canvas.style.height = cssH + 'px';
      slot.style.minHeight = cssH + 'px';

      const ctx = canvas.getContext('2d', { alpha: false });
      ctx.fillStyle = '#FFFFFF';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      await page.render({ canvasContext: ctx, viewport: vp }).promise;
      if (gen === undefined || gen === _pvRenderGen) PV.rendered.add(pNum);
    } catch (e) {
      console.error('Render page error', pNum, e);
    } finally {
      PV.rendering.delete(pNum);
    }
  }

  function pvRebuildLayout() {
    if (!PV.doc) return;
    _pvRenderGen++;
    _pvQueue = [];
    if (PV.io) PV.io.disconnect();
    PV.rendered.clear();
    PV.rendering.clear();
    pvPages.innerHTML = '';
    pvPages.className = `pv-pages theme-${PV.theme} mode-${PV.mode}`;

    const pagesToBuild = PV.mode === 'single' ? [PV.curPage] : Array.from({ length: PV.numPages }, (_, i) => i + 1);
    const estH = Math.round(Math.max(320, (pvPages.clientWidth - 16) * 1.414 * PV.zoom));

    const frag = document.createDocumentFragment();
    pagesToBuild.forEach(p => {
      const slot = document.createElement('div');
      slot.className = 'pv-page';
      slot.dataset.p = String(p);
      slot.style.minHeight = estH + 'px';
      slot.innerHTML = `<div class="pv-skel">Page ${p}</div>`;
      frag.appendChild(slot);
    });
    pvPages.appendChild(frag);

    PV.io = new IntersectionObserver(entries => {
      let topMost = null;
      entries.forEach(en => {
        const p = parseInt(en.target.dataset.p, 10);
        if (en.isIntersecting) {
          pvEnqueueRender(p);
          if (en.intersectionRatio > 0.2 && (topMost === null || p < topMost)) topMost = p;
        }
      });
      if (PV.mode === 'scroll' && topMost !== null && topMost !== PV.curPage) {
        PV.curPage = topMost;
        pvUpdateMeta();
      }
    }, { root: pvPages, rootMargin: '220px 0px', threshold: [0.01, 0.25] });

    pvPages.querySelectorAll('.pv-page').forEach(el => PV.io.observe(el));
    pvEnqueueRender(PV.curPage);
    if (PV.mode === 'scroll' && PV.curPage + 1 <= PV.numPages) pvEnqueueRender(PV.curPage + 1);
    pvUpdateMeta();
  }

  function pvJumpTo(p) {
    if (!PV.doc) return;
    const target = Math.max(1, Math.min(PV.numPages, p));
    PV.curPage = target;
    if (PV.mode === 'single') {
      pvRebuildLayout();
    } else {
      const el = pvPages.querySelector(`.pv-page[data-p="${target}"]`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        pvEnqueueRender(target);
      }
    }
    pvUpdateMeta();
  }

  async function pvBuildThumbs() {
    if (!PV.doc || PV.thumbsBuilt) return;
    PV.thumbsBuilt = true;
    pvThumbs.innerHTML = '';
    const cap = Math.min(PV.numPages, 60);
    for (let i = 1; i <= cap; i++) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'pv-thumb' + (i === PV.curPage ? ' active' : '');
      btn.dataset.p = String(i);
      btn.innerHTML = `<canvas></canvas><span>${i}</span>`;
      btn.addEventListener('click', () => pvJumpTo(i));
      pvThumbs.appendChild(btn);
      (async (pNum, c) => {
        try {
          const page = await PV.doc.getPage(pNum);
          const vp0 = page.getViewport({ scale: 1 });
          const sc = 72 / vp0.width;
          const vp = page.getViewport({ scale: sc });
          c.width = vp.width; c.height = vp.height;
          await page.render({ canvasContext: c.getContext('2d'), viewport: vp }).promise;
        } catch (_) {}
      })(i, btn.querySelector('canvas'));
    }
  }

  function pvShowLoadingSkeleton(name) {
    if (!pvStage || !pvPages) return;
    pvTitle.textContent = name || 'Loading PDF…';
    pvPagePill.textContent = '…';
    pvProgFill.style.width = '18%';
    pvStage.classList.remove('pv-immersive');
    pvThumbs.style.display = 'none';
    pvSearchBar.style.display = 'none';
    pvEmpty.style.display = 'none';
    pvStage.style.display = 'flex';
    pvPages.className = `pv-pages theme-${PV.theme} mode-${PV.mode}`;
    pvPages.innerHTML = `
      <div class="pv-load-wrap">
        <div class="pv-load-card">
          <div class="pv-shimmer-line title"></div>
          <div class="pv-shimmer-line"></div>
          <div class="pv-shimmer-line med"></div>
          <div class="pv-shimmer-line short"></div>
          <div class="pv-shimmer-block"></div>
          <div class="pv-shimmer-line"></div>
          <div class="pv-shimmer-line med"></div>
          <div class="pv-shimmer-line short"></div>
        </div>
        <div class="pv-load-card">
          <div class="pv-shimmer-line title"></div>
          <div class="pv-shimmer-line med"></div>
          <div class="pv-shimmer-line"></div>
          <div class="pv-shimmer-line short"></div>
        </div>
      </div>`;
  }

  let pendingLockedPdf = null;
  const pvPassModal = document.getElementById('pv-pass-modal');
  const pvPassInput = document.getElementById('pv-pass-input');
  const pvPassErr = document.getElementById('pv-pass-err');

  async function pvOpenBytes(uint8, filename, password) {
    if (!window['pdfjs-dist/build/pdf']) {
      showToast('PDF engine still loading…');
      return;
    }
    try {
      if (!password) { switchTab('viewer', { keepScroll: true }); pvShowLoadingSkeleton(filename); }
      const pdfjs = window['pdfjs-dist/build/pdf'];
      const opts = { data: uint8.slice() };
      if (password) opts.password = password;
      const doc = await pdfjs.getDocument(opts).promise;
      if (pvPassModal) pvPassModal.classList.remove('open');
      pendingLockedPdf = null;

      PV.doc = doc;
      PV.rawBytes = uint8;
      PV.name = filename || 'document.pdf';
      PV.numPages = doc.numPages;
      const resumed = getSavedPage(PV.name, uint8.length);
      PV.curPage = (resumed > 1 && resumed <= doc.numPages) ? resumed : 1;
      PV.zoom = 1.0;
      PV.rotation = 0;
      PV.textCache.clear();
      PV.matches = [];
      PV.matchIdx = -1;
      PV.thumbsBuilt = false;
      pvStage.classList.remove('pv-immersive');
      pvThumbs.style.display = 'none';
      pvSearchBar.style.display = 'none';
      pvSearchInput.value = '';
      pvSearchCount.textContent = '';

      pvTitle.textContent = PV.name;
      pvEmpty.style.display = 'none';
      pvStage.style.display = 'flex';
      switchTab('viewer', { keepScroll: true });
      requestAnimationFrame(() => {
        pvRebuildLayout();
        if (PV.curPage > 1) {
          setTimeout(() => pvJumpTo(PV.curPage), 80);
          showToast(`Resumed at Page ${PV.curPage}`, 1400);
        }
      });
    } catch (err) {
      if (err && (err.name === 'PasswordException' || /password/i.test(err.message || ''))) {
        pendingLockedPdf = { uint8, filename };
        if (pvPassErr) pvPassErr.textContent = password ? 'Incorrect password. Try again.' : '';
        if (pvPassInput) { pvPassInput.value = ''; setTimeout(() => pvPassInput.focus(), 120); }
        if (pvPassModal) pvPassModal.classList.add('open');
        return;
      }
      console.error(err);
      if (!PV.doc) { pvPages.innerHTML = ''; pvStage.style.display = 'none'; pvEmpty.style.display = 'flex'; }
      showToast('Could not open PDF', 2400, 'error');
    }
  }
  document.getElementById('pv-pass-cancel')?.addEventListener('click', () => {
    pvPassModal?.classList.remove('open');
    pendingLockedPdf = null;
    if (!PV.doc) {
      pvPages.innerHTML = '';
      pvStage.style.display = 'none';
      pvEmpty.style.display = 'flex';
    }
  });
  document.getElementById('pv-pass-unlock')?.addEventListener('click', () => {
    if (!pendingLockedPdf) return;
    pvOpenBytes(pendingLockedPdf.uint8, pendingLockedPdf.filename, pvPassInput?.value || '');
  });
  pvPassInput?.addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('pv-pass-unlock')?.click();
  });
  window.__pexiOpenPdfBytes = pvOpenBytes;

  document.getElementById('pv-file-input')?.addEventListener('change', async e => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    const buf = new Uint8Array(await f.arrayBuffer());
    await pvOpenBytes(buf, f.name);
    e.target.value = '';
  });

  const openLastPdf = async () => {
    if (typeof lastPdfBlob === 'undefined' || !lastPdfBlob) { showToast('Generate a PDF first'); return; }
    const buf = new Uint8Array(await lastPdfBlob.arrayBuffer());
    const nm = document.getElementById('res-name')?.textContent || 'output.pdf';
    await pvOpenBytes(buf, nm);
  };
  document.getElementById('pv-open-last')?.addEventListener('click', openLastPdf);
  document.getElementById('res-read-btn')?.addEventListener('click', openLastPdf);

  document.getElementById('pv-close-btn')?.addEventListener('click', () => {
    PV.doc = null; PV.rawBytes = null; PV.numPages = 0;
    pvPages.innerHTML = '';
    pvStage.style.display = 'none';
    pvEmpty.style.display = 'flex';
    refreshDevicePdfs();
  });

  pvThemeBtn?.addEventListener('click', () => {
    const order = ['orig', 'night', 'sepia'];
    const names = { orig: 'Original paper', night: 'OLED Night mode', sepia: 'Warm Sepia' };
    PV.theme = order[(order.indexOf(PV.theme) + 1) % order.length];
    pvThemeBtn.innerHTML = THEME_SVGS[PV.theme];
    pvPages.className = `pv-pages theme-${PV.theme} mode-${PV.mode}`;
    showToast(names[PV.theme], 1100);
  });

  pvModeBtn?.addEventListener('click', () => {
    PV.mode = PV.mode === 'scroll' ? 'single' : 'scroll';
    pvModeBtn.textContent = PV.mode === 'scroll' ? 'Scroll' : 'Page';
    pvRebuildLayout();
    showToast(PV.mode === 'scroll' ? 'Continuous scroll' : 'Single-page mode', 1100);
  });

  document.getElementById('pv-thumbs-btn')?.addEventListener('click', () => {
    const show = pvThumbs.style.display === 'none' || !pvThumbs.style.display;
    pvThumbs.style.display = show ? 'flex' : 'none';
    if (show) pvBuildThumbs();
  });

  document.getElementById('pv-search-btn')?.addEventListener('click', () => {
    const show = pvSearchBar.style.display === 'none' || !pvSearchBar.style.display;
    pvSearchBar.style.display = show ? 'flex' : 'none';
    if (show) pvSearchInput.focus();
  });

  async function pvRunSearch(query) {
    const q = (query || '').trim().toLowerCase();
    PV.matches = []; PV.matchIdx = -1;
    if (!q || !PV.doc) { pvSearchCount.textContent = ''; return; }
    pvSearchCount.textContent = '…';
    for (let p = 1; p <= PV.numPages; p++) {
      let txt = PV.textCache.get(p);
      if (txt === undefined) {
        const page = await PV.doc.getPage(p);
        const content = await page.getTextContent();
        txt = content.items.map(it => it.str).join(' ');
        PV.textCache.set(p, txt);
      }
      if (txt.toLowerCase().includes(q)) PV.matches.push(p);
    }
    if (!PV.matches.length) {
      pvSearchCount.textContent = '0 matches';
    } else {
      PV.matchIdx = 0;
      pvSearchCount.textContent = `1 / ${PV.matches.length} pg`;
      pvJumpTo(PV.matches[0]);
    }
  }
  let _searchTimer = null;
  pvSearchInput?.addEventListener('input', () => {
    clearTimeout(_searchTimer);
    _searchTimer = setTimeout(() => pvRunSearch(pvSearchInput.value), 280);
  });
  document.getElementById('pv-search-prev')?.addEventListener('click', () => {
    if (!PV.matches.length) return;
    PV.matchIdx = (PV.matchIdx - 1 + PV.matches.length) % PV.matches.length;
    pvSearchCount.textContent = `${PV.matchIdx + 1} / ${PV.matches.length} pg`;
    pvJumpTo(PV.matches[PV.matchIdx]);
  });
  document.getElementById('pv-search-next')?.addEventListener('click', () => {
    if (!PV.matches.length) return;
    PV.matchIdx = (PV.matchIdx + 1) % PV.matches.length;
    pvSearchCount.textContent = `${PV.matchIdx + 1} / ${PV.matches.length} pg`;
    pvJumpTo(PV.matches[PV.matchIdx]);
  });

  document.getElementById('pv-copy-btn')?.addEventListener('click', async () => {
    if (!PV.doc) return;
    try {
      let txt = PV.textCache.get(PV.curPage);
      if (txt === undefined) {
        const page = await PV.doc.getPage(PV.curPage);
        const content = await page.getTextContent();
        txt = content.items.map(it => it.str).join(' ').trim();
        PV.textCache.set(PV.curPage, txt);
      }
      if (!txt) { showToast('No selectable text on this page'); return; }
      await navigator.clipboard.writeText(txt);
      showToast(`Copied Page ${PV.curPage} text`);
    } catch (_) {
      showToast('Could not copy text');
    }
  });

  const pvJumpModal = document.getElementById('pv-jump-modal');
  const pvJumpInput = document.getElementById('pv-jump-input');
  const pvJumpSub = document.getElementById('pv-jump-sub');
  pvPagePill?.addEventListener('click', () => {
    if (!PV.numPages || !pvJumpModal) return;
    if (pvJumpSub) pvJumpSub.textContent = `Enter a page number between 1 and ${PV.numPages}`;
    if (pvJumpInput) {
      pvJumpInput.min = '1';
      pvJumpInput.max = String(PV.numPages);
      pvJumpInput.value = String(PV.curPage);
      setTimeout(() => { pvJumpInput.focus(); pvJumpInput.select(); }, 100);
    }
    pvJumpModal.classList.add('open');
  });
  document.getElementById('pv-jump-cancel')?.addEventListener('click', () => pvJumpModal?.classList.remove('open'));
  document.getElementById('pv-jump-first')?.addEventListener('click', () => { pvJumpModal?.classList.remove('open'); pvJumpTo(1); });
  document.getElementById('pv-jump-last')?.addEventListener('click', () => { pvJumpModal?.classList.remove('open'); pvJumpTo(PV.numPages); });
  document.getElementById('pv-jump-go')?.addEventListener('click', () => {
    const n = parseInt(pvJumpInput?.value || '', 10);
    if (!isNaN(n) && n >= 1 && n <= PV.numPages) {
      pvJumpModal?.classList.remove('open');
      pvJumpTo(n);
    } else {
      showToast(`Enter 1–${PV.numPages}`, 1200);
    }
  });
  pvJumpInput?.addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('pv-jump-go')?.click();
  });

  document.getElementById('pv-share-btn')?.addEventListener('click', async () => {
    if (!PV.rawBytes) return;
    const blob = new Blob([PV.rawBytes], { type: 'application/pdf' });
    if (window.__pexiShareBlob) {
      await window.__pexiShareBlob(blob, PV.name || 'document.pdf', 'application/pdf');
    } else {
      showToast('Share is available in the Android app');
    }
  });

  document.getElementById('pv-rot-btn')?.addEventListener('click', () => {
    if (!PV.doc) return;
    PV.rotation = (PV.rotation + 90) % 360;
    pvRebuildLayout();
    showToast(`Rotated ${PV.rotation}°`, 900);
  });

  const setZoom = z => {
    PV.zoom = Math.max(0.6, Math.min(3.2, Math.round(z * 100) / 100));
    pvRebuildLayout();
  };
  document.getElementById('pv-prev')?.addEventListener('click', () => pvJumpTo(PV.curPage - 1));
  document.getElementById('pv-next')?.addEventListener('click', () => pvJumpTo(PV.curPage + 1));
  document.getElementById('pv-zout')?.addEventListener('click', () => setZoom(PV.zoom - 0.25));
  document.getElementById('pv-zin')?.addEventListener('click', () => setZoom(PV.zoom + 0.25));
  pvZoomLabel?.addEventListener('click', () => setZoom(1.0));

  // Compositor-friendly pinch-to-zoom, single-page swipe, double-tap zoom, and single-tap immersive mode
  let _lastTap = 0;
  let _tapTimer = null;
  let _touchStartX = 0, _touchStartY = 0, _touchMoved = false;
  let _pinchDist0 = 0, _pinchScale = 1, _isPinching = false;

  function onPinchMove(e) {
    if (_isPinching && e.touches.length === 2) {
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      const dist = Math.hypot(dx, dy) || 1;
      _pinchScale = Math.max(0.55, Math.min(2.6, dist / _pinchDist0));
      pvPages.style.transform = `scale(${_pinchScale.toFixed(3)})`;
      pvPages.style.transformOrigin = 'center top';
      e.preventDefault();
    }
  }

  pvPages?.addEventListener('touchstart', e => {
    if (e.touches.length === 2) {
      _isPinching = true;
      _touchMoved = true;
      clearTimeout(_tapTimer);
      const dx = e.touches[0].clientX - e.touches[1].clientX;
      const dy = e.touches[0].clientY - e.touches[1].clientY;
      _pinchDist0 = Math.hypot(dx, dy) || 1;
      _pinchScale = 1;
      pvPages.addEventListener('touchmove', onPinchMove, { passive: false });
    } else if (e.touches.length === 1) {
      _isPinching = false;
      _touchMoved = false;
      _touchStartX = e.touches[0].clientX;
      _touchStartY = e.touches[0].clientY;
    }
  }, { passive: true });

  pvPages?.addEventListener('touchmove', e => {
    if (!_isPinching && e.touches.length === 1) {
      const dx = Math.abs(e.touches[0].clientX - _touchStartX);
      const dy = Math.abs(e.touches[0].clientY - _touchStartY);
      if (dx > 12 || dy > 12) _touchMoved = true;
    }
  }, { passive: true });

  function finishPinch() {
    pvPages?.removeEventListener('touchmove', onPinchMove, { passive: false });
    _isPinching = false;
    if (pvPages) {
      pvPages.style.transform = '';
      pvPages.style.transformOrigin = '';
    }
    if (Math.abs(_pinchScale - 1) > 0.08) {
      setZoom(PV.zoom * _pinchScale);
    }
    _pinchScale = 1;
  }

  pvPages?.addEventListener('touchcancel', () => {
    if (_isPinching) finishPinch();
  }, { passive: true });

  pvPages?.addEventListener('touchend', e => {
    if (_isPinching) {
      if (e.touches.length < 2) finishPinch();
      return;
    }
    if (e.touches.length > 0) return;

    if (PV.mode === 'single' && PV.zoom <= 1.08 && e.changedTouches && e.changedTouches[0]) {
      const dx = e.changedTouches[0].clientX - _touchStartX;
      const dy = Math.abs(e.changedTouches[0].clientY - _touchStartY);
      if (Math.abs(dx) > 58 && dy < 70) {
        pvJumpTo(dx < 0 ? PV.curPage + 1 : PV.curPage - 1);
        return;
      }
    }
    if (_touchMoved) return;

    const now = Date.now();
    if (now - _lastTap < 270) {
      clearTimeout(_tapTimer);
      setZoom(PV.zoom > 1.2 ? 1.0 : 1.75);
      _lastTap = 0;
    } else {
      _lastTap = now;
      _tapTimer = setTimeout(() => {
        if (PV.doc) pvStage.classList.toggle('pv-immersive');
      }, 280);
    }
  }, { passive: true });

  let extPdfChunks = [];
  let extPdfName = 'document.pdf';
  window.__pexiExternalPdfStart = function (name) {
    extPdfChunks = [];
    extPdfName = name || 'document.pdf';
    switchTab('viewer', { keepScroll: true });
    pvShowLoadingSkeleton(extPdfName);
  };
  window.__pexiExternalPdfChunk = function (b64) {
    extPdfChunks.push(b64);
  };
  window.__pexiExternalPdfEnd = function () {
    try {
      const parts = extPdfChunks.map(c => {
        const bin = atob(c);
        const arr = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
        return arr;
      });
      extPdfChunks = [];
      const total = parts.reduce((s, a) => s + a.length, 0);
      const merged = new Uint8Array(total);
      let off = 0;
      for (const a of parts) { merged.set(a, off); off += a.length; }
      pvOpenBytes(merged, extPdfName);
    } catch (e) {
      console.error(e);
      showToast('Failed to open PDF');
    }
  };

  window.__pexiBack = function () {
    if (pvPassModal && pvPassModal.classList.contains('open')) {
      document.getElementById('pv-pass-cancel')?.click();
      return true;
    }
    if (pvJumpModal && pvJumpModal.classList.contains('open')) {
      pvJumpModal.classList.remove('open');
      return true;
    }
    const lb = document.getElementById('lightbox');
    if (lb && lb.style.display === 'flex') {
      document.getElementById('lightbox-close')?.click();
      return true;
    }
    const modals = [
      ['about-modal', 'about-close-btn'],
      ['name-modal', 'name-cancel-btn'],
      ['crop-modal', 'crop-cancel-btn'],
      ['text-modal', 'text-cancel-btn'],
      ['compress-modal', 'compress-close-btn'],
      ['compress-video-modal', 'compress-video-close-btn'],
      ['gt-modal', 'gt-close'],
      ['camera-modal', 'cam-close-btn']
    ];
    for (const [mid, cid] of modals) {
      const m = document.getElementById(mid);
      if (m && m.style.display && m.style.display !== 'none') {
        document.getElementById(cid)?.click();
        return true;
      }
    }
    if (activeTab === 'viewer' && PV.doc) {
      document.getElementById('pv-close-btn')?.click();
      return true;
    }
    if (activeTab !== 'home') {
      switchTab('home');
      return true;
    }
    return false;
  };

  function blobToBase64(blob) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => {
        const res = String(r.result || '');
        const idx = res.indexOf(',');
        resolve(idx >= 0 ? res.slice(idx + 1) : res);
      };
      r.onerror = () => reject(r.error);
      r.readAsDataURL(blob);
    });
  }

  async function streamBlobToAndroid(blob, filename, mime, mode) {
    if (window.PexiBridge && window.PexiBridge.beginTransfer) {
      const id = 'tx_' + Date.now() + '_' + Math.random().toString(36).slice(2, 7);
      const chunkBytes = 384 * 1024;
      window.PexiBridge.beginTransfer(id, filename || 'pexipdf_output', mime || blob.type || 'application/octet-stream', mode);
      for (let off = 0; off < blob.size; off += chunkBytes) {
        const slice = blob.slice(off, Math.min(blob.size, off + chunkBytes));
        const b64 = await blobToBase64(slice);
        window.PexiBridge.appendTransfer(id, b64);
      }
      window.PexiBridge.finishTransfer(id);
      return;
    }
    const b64 = await blobToBase64(blob);
    if (mode === 'share') window.PexiBridge.shareFile(b64, filename, mime);
    else window.PexiBridge.saveFile(b64, filename, mime);
  }

  window.__pexiShareBlob = async function (blob, filename, mime) {
    try {
      showToast('Preparing share…', 1500);
      await streamBlobToAndroid(blob, filename || 'PexiPDF_output.pdf', mime || blob.type || 'application/pdf', 'share');
    } catch (err) {
      showToast('Could not share file');
    }
  };

  function interceptAndroidDownload(anchorId) {
    const a = document.getElementById(anchorId);
    if (!a) return;
    a.addEventListener('click', async e => {
      if (!window.PexiBridge || (!window.PexiBridge.saveFile && !window.PexiBridge.beginTransfer)) return;
      const href = a.getAttribute('href') || '';
      if (!href.startsWith('blob:')) return;
      e.preventDefault();
      try {
        showToast('Saving to Downloads/PexiPDF…', 1800);
        const resp = await fetch(href);
        const blob = await resp.blob();
        const fname = a.getAttribute('download') || 'pexipdf_output';
        const mime = blob.type || 'application/octet-stream';
        await streamBlobToAndroid(blob, fname, mime, 'save');
      } catch (err) {
        console.error(err);
        showToast('Save failed');
      }
    });
  }
  ['dl-btn', 'compress-dl-btn', 'compress-video-dl-btn', 'gt-dl'].forEach(interceptAndroidDownload);

  const verEl = document.getElementById('app-version-label');
  const aboutVerEl = document.getElementById('about-version-pill');
  const updateBtn = document.getElementById('settings-update-row');
  const aboutUpdateBtn = document.getElementById('about-update-btn');
  const nativeCamBtn = document.getElementById('cam-native-btn');
  if (window.PexiBridge) {
    document.documentElement.classList.add('is-android-app');
    if (nativeCamBtn) nativeCamBtn.style.display = 'inline-flex';
    try {
      const v = window.PexiBridge.getAppVersion ? window.PexiBridge.getAppVersion() : '1.0.0';
      if (verEl) verEl.textContent = 'v' + v;
      if (aboutVerEl) aboutVerEl.textContent = 'Android App · v' + v;
    } catch (_) {}
    if (window.PexiBridge.onReady) {
      setTimeout(() => { try { window.PexiBridge.onReady(); } catch (_) {} }, 120);
    }
  }
  const triggerUpdateCheck = () => {
    if (window.PexiBridge && window.PexiBridge.checkForUpdates) {
      showToast('Checking GitHub Releases…', 1800);
      window.PexiBridge.checkForUpdates();
    } else {
      window.open('https://github.com/Xcluice/pexipdf/releases/latest', '_blank', 'noopener');
    }
  };
  if (updateBtn) updateBtn.addEventListener('click', triggerUpdateCheck);
  if (aboutUpdateBtn) aboutUpdateBtn.addEventListener('click', triggerUpdateCheck);

  window.__pexiSyncPages(typeof images !== 'undefined' ? images.length : 0);
})();
