#!/usr/bin/env python3
"""Idempotent Android app-style UI restyler for PexiPDF by Xcluice."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
ASSETS_OUT = ROOT / "app/src/main/assets/index.html"

orig_html = SRC.read_text(encoding="utf-8")
m = re.search(r'<script>\s*\n(// ─── GLOBAL CONTROL[\s\S]*?)</script>\s*\n</body>', orig_html)
assert m, "Could not locate main <script> block in index.html"
orig_js = m.group(1)
if "// ─── ANDROID APP SHELL" in orig_js:
    orig_js = orig_js.split("// ─── ANDROID APP SHELL")[0].rstrip()

# Idempotent surgical hooks
if "settings-dark-toggle" not in orig_js:
    orig_js = orig_js.replace(
        "localStorage.setItem('pexipdf_theme', isDark ? 'dark' : 'light');",
        "localStorage.setItem('pexipdf_theme', isDark ? 'dark' : 'light');\n"
        "  const st = document.getElementById('settings-dark-toggle'); if (st) st.checked = !!isDark;\n"
        "  const mc = document.querySelector('meta[name=\"theme-color\"]'); if (mc) mc.setAttribute('content', isDark ? '#0A0A0A' : '#F4F4F4');\n"
        "  if (window.PexiBridge && window.PexiBridge.setTheme) { try { window.PexiBridge.setTheme(!!isDark); } catch(_){} }"
    )

if "https://pexipdf.vercel.app" not in orig_js:
    orig_js = orig_js.replace(
        "corePath: location.origin + '/vendor/ffmpeg-core/ffmpeg-core.js',",
        "corePath: (window.PexiBridge ? 'https://pexipdf.vercel.app' : location.origin) + '/vendor/ffmpeg-core/ffmpeg-core.js',"
    )

if "window.__pexiSyncPages" not in orig_js:
    orig_js = orig_js.replace(
        "function renderGrid() {",
        "function renderGrid() {\n  if (window.__pexiSyncPages) window.__pexiSyncPages(images.length);"
    )
    orig_js = orig_js.replace(
        "updateEstSize();",
        "updateEstSize(); if (window.__pexiSyncPages) window.__pexiSyncPages(images.length);"
    )

if "window.__pexiShareBlob" not in orig_js:
    orig_js = orig_js.replace(
        "if (navigator.share) await navigator.share({ files: [new File([lastPdfBlob], fileName, { type: 'application/pdf' })], title: fileName }).catch(() => {});",
        "if (window.PexiBridge && window.PexiBridge.shareFile && lastPdfBlob) { window.__pexiShareBlob(lastPdfBlob, fileName, 'application/pdf'); return; }\n"
        "  if (navigator.share) await navigator.share({ files: [new File([lastPdfBlob], fileName, { type: 'application/pdf' })], title: fileName }).catch(() => {});"
    )

ANDROID_BRIDGE_JS = r"""
// ─── ANDROID APP SHELL · TABS · BOTTOM SHEETS · NATIVE BRIDGE ────────────────
(function () {
  const tabs = ['home', 'pages', 'tools', 'settings'];
  let activeTab = 'home';
  let prevPageCount = 0;

  function switchTab(tab, opts) {
    if (!tabs.includes(tab)) return;
    activeTab = tab;
    document.querySelectorAll('.app-screen').forEach(s => {
      const on = s.dataset.screen === tab;
      s.classList.toggle('active', on);
      if (on) {
        s.style.animation = 'none';
        void s.offsetWidth;
        s.style.animation = '';
      }
    });
    document.querySelectorAll('.bnav-item').forEach(b => {
      b.classList.toggle('active', b.dataset.tab === tab);
      b.setAttribute('aria-selected', b.dataset.tab === tab ? 'true' : 'false');
    });
    const scrollEl = document.getElementById('app-scroll');
    if (scrollEl && !(opts && opts.keepScroll)) scrollEl.scrollTop = 0;
  }
  window.__pexiSwitchTab = switchTab;

  document.querySelectorAll('.bnav-item').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  window.__pexiSyncPages = function (n) {
    const badge = document.getElementById('nav-pages-badge');
    const topPill = document.getElementById('top-pages-pill');
    const topPillNum = document.getElementById('top-pages-num');
    const banner = document.getElementById('home-workspace-banner');
    const bannerCount = document.getElementById('home-ws-count');
    if (badge) {
      badge.textContent = n > 99 ? '99+' : String(n);
      badge.style.display = n > 0 ? 'flex' : 'none';
    }
    if (topPill && topPillNum) {
      topPillNum.textContent = n + (n === 1 ? ' page' : ' pages');
      topPill.style.display = n > 0 ? 'inline-flex' : 'none';
    }
    if (banner && bannerCount) {
      banner.style.display = n > 0 ? 'flex' : 'none';
      bannerCount.textContent = n + (n === 1 ? ' page in workspace' : ' pages in workspace');
    }
    if (n > prevPageCount && prevPageCount === 0 && (activeTab === 'home' || activeTab === 'tools')) {
      setTimeout(() => switchTab('pages'), 180);
    }
    prevPageCount = n;
  };

  const topPill = document.getElementById('top-pages-pill');
  if (topPill) topPill.addEventListener('click', () => switchTab('pages'));
  const wsBtn = document.getElementById('home-workspace-banner');
  if (wsBtn) wsBtn.addEventListener('click', () => switchTab('pages'));

  const addMoreBtn = document.getElementById('pages-add-btn');
  if (addMoreBtn) addMoreBtn.addEventListener('click', () => document.getElementById('file-input').click());
  const emptyBrowseBtn = document.getElementById('empty-browse-btn');
  if (emptyBrowseBtn) emptyBrowseBtn.addEventListener('click', () => document.getElementById('file-input').click());
  const emptyCamBtn = document.getElementById('empty-cam-btn');
  if (emptyCamBtn) emptyCamBtn.addEventListener('click', () => document.getElementById('btn-camera').click());

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
    });
  });

  window.__pexiBack = function () {
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

  window.__pexiShareBlob = async function (blob, filename, mime) {
    try {
      showToast('Preparing share…', 1500);
      const b64 = await blobToBase64(blob);
      window.PexiBridge.shareFile(b64, filename || 'PexiPDF_output.pdf', mime || blob.type || 'application/pdf');
    } catch (err) {
      showToast('Could not share file');
    }
  };

  function interceptAndroidDownload(anchorId) {
    const a = document.getElementById(anchorId);
    if (!a) return;
    a.addEventListener('click', async e => {
      if (!window.PexiBridge || !window.PexiBridge.saveFile) return;
      const href = a.getAttribute('href') || '';
      if (!href.startsWith('blob:')) return;
      e.preventDefault();
      try {
        showToast('Saving to Downloads/PexiPDF…', 1800);
        const resp = await fetch(href);
        const blob = await resp.blob();
        const b64 = await blobToBase64(blob);
        const fname = a.getAttribute('download') || 'pexipdf_output';
        const mime = blob.type || 'application/octet-stream';
        window.PexiBridge.saveFile(b64, fname, mime);
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
  if (window.PexiBridge) {
    document.documentElement.classList.add('is-android-app');
    try {
      const v = window.PexiBridge.getAppVersion ? window.PexiBridge.getAppVersion() : '1.0.0';
      if (verEl) verEl.textContent = 'v' + v;
      if (aboutVerEl) aboutVerEl.textContent = 'Android App · v' + v;
    } catch (_) {}
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
"""

NEW_HEAD_AND_BODY = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
<title>PexiPDF by Xcluice — Offline PDF &amp; Media Studio</title>
<meta name="description" content="Convert JPG, PNG, and WEBP images or existing documents into compressed PDFs instantly. 100% offline, private, and free by Xcluice.">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48.png">
<link rel="icon" type="image/png" sizes="512x512" href="/favicon.png">
<link rel="apple-touch-icon" href="/apple-touch-icon.png">
<meta name="theme-color" content="#0A0A0A">
<meta name="mobile-web-app-capable" content="yes">

<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebApplication",
  "name": "PexiPDF by Xcluice",
  "url": "https://pexipdf.vercel.app/",
  "applicationCategory": "UtilitiesApplication"
}
</script>

<link href="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.css" rel="stylesheet" crossorigin="anonymous">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap" rel="stylesheet" crossorigin="anonymous">

<style>
  /* PexiPDF by Xcluice · Native Android App-Style UI (One UI / Material 3) */
  :root {
    --bg: #F4F4F5;
    --surface: #FFFFFF;
    --surface-elev: #FFFFFF;
    --surface-sunken: #ECECEE;
    --border: #E2E2E6;
    --border-strong: #CCCCD4;
    --text: #0B0B0D;
    --muted: #666670;
    --ink: #0B0B0D;
    --on-ink: #FFFFFF;
    --accent: #2F4ACB;
    --accent-2: #1D34A3;
    --accent-soft: rgba(47, 74, 203, 0.10);
    --red: #C93B3B;
    --green: #25855A;
    --amber: #B87B1F;
    --bar-bg: rgba(244, 244, 245, 0.86);
    --sheet-scrim: rgba(0, 0, 0, 0.56);
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 12px 32px rgba(0, 0, 0, 0.14);
    --ease: cubic-bezier(0.22, 1, 0.36, 1);
    --spring: cubic-bezier(0.34, 1.48, 0.64, 1);
    --safe-top: env(safe-area-inset-top, 0px);
    --safe-bot: env(safe-area-inset-bottom, 0px);
    --topbar-h: 60px;
    --bnav-h: 68px;
  }

  :root.dark {
    --bg: #0A0A0C;
    --surface: #141417;
    --surface-elev: #1A1A1E;
    --surface-sunken: #0F0F12;
    --border: #242429;
    --border-strong: #36363E;
    --text: #F4F4F6;
    --muted: #8E8E98;
    --ink: #F4F4F6;
    --on-ink: #0A0A0C;
    --accent: #8EA2FF;
    --accent-2: #B3C1FF;
    --accent-soft: rgba(142, 162, 255, 0.14);
    --red: #E8696A;
    --green: #4DB887;
    --amber: #E0A84B;
    --bar-bg: rgba(10, 10, 12, 0.86);
    --sheet-scrim: rgba(0, 0, 0, 0.74);
    --shadow: 0 1px 2px rgba(0, 0, 0, 0.45);
    --shadow-md: 0 16px 40px rgba(0, 0, 0, 0.65);
  }

  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-tap-highlight-color: transparent; -webkit-tap-highlight-color: rgba(0, 0, 0, 0); }
  a, button, input, select, textarea, label, summary, [role="button"] { -webkit-tap-highlight-color: transparent; -webkit-touch-callout: none; }
  button { font: inherit; }

  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.001ms !important; animation-iteration-count: 1 !important; transition-duration: 0.001ms !important; }
  }

  html, body {
    height: 100%; overflow: hidden; background: var(--bg); color: var(--text);
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Roboto', system-ui, sans-serif;
    font-size: 14px; -webkit-font-smoothing: antialiased; overscroll-behavior-y: none; user-select: none;
  }
  input, textarea { user-select: text; }

  #aurora { position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden; }
  #aurora::before {
    content: ''; position: absolute; inset: -32px;
    background-image: radial-gradient(circle, var(--border) 1px, transparent 1.4px);
    background-size: 26px 26px; opacity: 0.55; animation: gridDrift 45s linear infinite;
    -webkit-mask-image: radial-gradient(ellipse at 50% 0%, #000 0%, transparent 72%);
            mask-image: radial-gradient(ellipse at 50% 0%, #000 0%, transparent 72%);
  }
  @keyframes gridDrift { to { transform: translate(26px, 26px); } }

  .app-shell {
    position: relative; z-index: 2; height: 100%; width: 100%; max-width: 540px;
    margin: 0 auto; display: flex; flex-direction: column;
  }

  .app-topbar {
    position: sticky; top: 0; z-index: 30; height: calc(var(--topbar-h) + var(--safe-top));
    padding: var(--safe-top) 16px 0; display: flex; align-items: center; gap: 11px;
    background: var(--bar-bg); backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .app-brand-mark {
    width: 36px; height: 36px; border-radius: 11px; background: var(--ink); color: var(--on-ink);
    display: grid; place-items: center; flex-shrink: 0; box-shadow: var(--shadow);
  }
  .app-brand-mark svg { width: 20px; height: 20px; display: block; }
  .topbar-titles { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 1px; }
  .topbar-title-row { display: flex; align-items: baseline; gap: 6px; }
  .header-title { font-family: 'Fraunces', serif; font-size: 20px; font-weight: 600; line-height: 1.1; letter-spacing: -0.4px; color: var(--text); }
  .header-title span { color: var(--accent); }
  .xcluice-tag { font-size: 10px; font-weight: 600; color: var(--muted); letter-spacing: 0.2px; }
  .header-sub { font-size: 11px; color: var(--muted); display: flex; align-items: center; gap: 6px; white-space: nowrap; overflow: hidden; }
  .tagline { display: inline-block; animation: flipIn .45s var(--ease) both; overflow: hidden; text-overflow: ellipsis; }
  @keyframes flipIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: none; } }

  .topbar-actions { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
  .top-pill {
    display: none; align-items: center; gap: 5px; height: 32px; padding: 0 11px; border-radius: 999px;
    background: var(--accent-soft); color: var(--accent); border: 1px solid transparent;
    font-size: 11.5px; font-weight: 600; cursor: pointer; transition: transform .2s var(--spring);
  }
  .top-pill:active { transform: scale(0.94); }
  .top-pill .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--accent); }
  .icon-btn {
    width: 36px; height: 36px; border-radius: 50%; background: var(--surface); border: 1px solid var(--border);
    color: var(--text); display: grid; place-items: center; cursor: pointer; font-size: 15px;
    transition: transform .25s var(--spring), border-color .2s;
  }
  .icon-btn:active { transform: scale(0.9); }
  .icon-btn svg { width: 17px; height: 17px; }

  #app-scroll {
    flex: 1; overflow-y: auto; overflow-x: hidden; -webkit-overflow-scrolling: touch;
    padding: 16px 16px calc(var(--bnav-h) + var(--safe-bot) + 24px); scroll-behavior: smooth;
  }
  #app-scroll::-webkit-scrollbar { width: 0; height: 0; }

  .app-screen { display: none; flex-direction: column; gap: 16px; }
  .app-screen.active { display: flex; animation: screenEnter .32s var(--ease) both; }
  @keyframes screenEnter { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }

  .section-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: -6px; padding: 2px 2px 0; }
  .section-label { font-size: 11.5px; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase; color: var(--muted); }
  .offline-pill {
    display: inline-flex; align-items: center; gap: 5px; font-size: 10px; font-weight: 600;
    color: var(--muted); background: var(--surface); border: 1px solid var(--border); padding: 3px 9px; border-radius: 999px;
  }
  .offline-pill::before { content: ''; width: 6px; height: 6px; border-radius: 50%; background: var(--green); animation: dotPulse 2.4s ease-out infinite; }
  @keyframes dotPulse { 0% { box-shadow: 0 0 0 0 rgba(77, 184, 135, 0.55); } 75%, 100% { box-shadow: 0 0 0 6px rgba(77, 184, 135, 0); } }

  #dropzone.hero-card {
    position: relative; overflow: hidden; background: var(--ink); color: var(--on-ink);
    border: 1px solid var(--ink); border-radius: 26px; padding: 22px 20px 20px; min-height: 158px;
    display: flex; flex-direction: column; justify-content: space-between; gap: 14px;
    cursor: pointer; box-shadow: var(--shadow-md); transition: transform .25s var(--ease);
  }
  #dropzone.hero-card:active, #dropzone.hero-card.hover { transform: scale(0.985); }
  #dropzone input[type="file"] { position: absolute; inset: 0; opacity: 0; cursor: pointer; z-index: 5; }
  .hero-top { display: flex; align-items: flex-start; justify-content: space-between; position: relative; z-index: 2; }
  .drop-icon {
    width: 46px; height: 46px; padding: 11px; border-radius: 15px;
    background: rgba(128, 128, 128, 0.18); border: 1px solid rgba(128, 128, 128, 0.34);
    color: var(--on-ink); display: grid; place-items: center;
  }
  .drop-icon svg { width: 100%; height: 100%; }
  .hero-chip { font-size: 10.5px; font-weight: 600; padding: 5px 10px; border-radius: 999px; background: rgba(128, 128, 128, 0.18); color: var(--on-ink); }
  .hero-copy { position: relative; z-index: 2; }
  .drop-title { font-size: 18px; font-weight: 700; letter-spacing: -0.25px; color: var(--on-ink); }
  .drop-sub { font-size: 12px; color: var(--on-ink); opacity: 0.72; margin-top: 3px; }
  #dropzone .ring {
    position: absolute; right: 24px; top: 24px; width: 46px; height: 46px; border-radius: 50%;
    border: 1.5px solid var(--on-ink); opacity: 0; animation: ring 3s ease-out infinite; pointer-events: none;
  }
  #dropzone .ring.r2 { animation-delay: 1.5s; }
  @keyframes ring { 0% { transform: scale(.55); opacity: .55; } 100% { transform: scale(2.8); opacity: 0; } }

  #home-workspace-banner {
    display: none; align-items: center; gap: 12px; background: var(--surface); border: 1px solid var(--accent);
    border-radius: 18px; padding: 13px 15px; cursor: pointer; box-shadow: var(--shadow); transition: transform .2s var(--spring);
  }
  #home-workspace-banner:active { transform: scale(0.98); }
  .ws-icon { width: 36px; height: 36px; border-radius: 11px; background: var(--accent-soft); color: var(--accent); display: grid; place-items: center; flex-shrink: 0; }
  .ws-info { flex: 1; min-width: 0; }
  .ws-title { font-size: 13.5px; font-weight: 600; color: var(--text); }
  .ws-sub { font-size: 11.5px; color: var(--muted); margin-top: 1px; }
  .ws-go { font-size: 12px; font-weight: 600; color: var(--accent); white-space: nowrap; }

  .tool-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 11px; width: 100%; }
  .tool {
    --c1: var(--accent); position: relative; overflow: hidden; border: 1px solid var(--border); border-radius: 22px;
    padding: 16px 15px; min-height: 116px; color: var(--text); text-align: left; cursor: pointer;
    display: flex; flex-direction: column; justify-content: space-between; gap: 10px;
    background: var(--surface); box-shadow: var(--shadow); transition: transform .22s var(--spring), border-color .2s;
  }
  .tool:active { transform: scale(0.96); border-color: var(--border-strong); background: var(--surface-elev); }
  .tool .t-ico-wrap {
    width: 38px; height: 38px; border-radius: 12px; background: var(--surface-sunken);
    border: 1px solid var(--border); display: grid; place-items: center; position: relative; color: var(--text);
  }
  .tool .t-ico-wrap::after { content: ''; position: absolute; top: -3px; right: -3px; width: 9px; height: 9px; border-radius: 50%; background: var(--c1); border: 2px solid var(--surface); }
  .tool .t-ico { width: 19px; height: 19px; display: block; }
  .tool .t-name { font-weight: 600; font-size: 14px; color: var(--text); line-height: 1.2; }
  .tool .t-desc { font-size: 11.5px; color: var(--muted); line-height: 1.3; margin-top: 2px; }
  .tool-camera { --c1: #2E8B62; } .tool-text { --c1: #C98A2B; } .tool-pdfc { --c1: #2F4ACB; } .tool-vidc { --c1: #C93B3B; }

  .marquee { width: 100%; overflow: hidden; padding: 2px 0; -webkit-mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent); mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent); }
  .marquee .track { display: flex; gap: 8px; width: max-content; animation: marq 34s linear infinite; }
  .chip { white-space: nowrap; font-size: 11px; font-weight: 500; padding: 6px 12px 6px 22px; border-radius: 999px; color: var(--muted); background: var(--surface); border: 1px solid var(--border); position: relative; }
  .chip::before { content: ''; position: absolute; left: 9px; top: 50%; width: 5px; height: 5px; margin-top: -2.5px; border-radius: 50%; background: var(--accent); }
  .chip:nth-child(3n+2)::before { background: var(--green); } .chip:nth-child(3n+3)::before { background: var(--amber); }
  @keyframes marq { to { transform: translateX(-50%); } }

  .android-group { background: var(--surface); border: 1px solid var(--border); border-radius: 22px; overflow: hidden; box-shadow: var(--shadow); }
  .tool-row {
    width: 100%; background: transparent; border: none; border-bottom: 1px solid var(--border);
    padding: 14px 16px; display: flex; align-items: center; gap: 13px; text-align: left; color: var(--text); cursor: pointer;
  }
  .tool-row:last-child { border-bottom: none; }
  .tool-row:active { background: var(--surface-sunken); }
  .tr-ico { width: 40px; height: 40px; border-radius: 13px; background: var(--surface-sunken); border: 1px solid var(--border); display: grid; place-items: center; flex-shrink: 0; color: var(--text); position: relative; }
  .tr-ico svg { width: 19px; height: 19px; }
  .tr-ico::after { content: ''; position: absolute; top: -2px; right: -2px; width: 8px; height: 8px; border-radius: 50%; background: var(--c1, var(--accent)); border: 2px solid var(--surface); }
  .tr-body { flex: 1; min-width: 0; }
  .tr-title { font-size: 14px; font-weight: 600; color: var(--text); display: flex; align-items: center; gap: 7px; }
  .tr-sub { font-size: 12px; color: var(--muted); margin-top: 2px; }
  .tr-chev { color: var(--muted); font-size: 18px; line-height: 1; flex-shrink: 0; opacity: 0.7; }
  .tag-pill { font-size: 9px; font-weight: 700; letter-spacing: 0.5px; padding: 2px 6px; border-radius: 999px; background: var(--accent-soft); color: var(--accent); }

  #est-size-bar { display: none; align-items: center; gap: 8px; font-size: 12px; color: var(--muted); padding: 11px 14px; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; box-shadow: var(--shadow); }
  #est-size-val { font-weight: 700; color: var(--text); font-variant-numeric: tabular-nums; }

  #preview-section { display: none; flex-direction: column; gap: 14px; width: 100%; }
  .preview-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
  .pages-title { font-size: 16px; font-weight: 700; color: var(--text); }
  .preview-actions { display: flex; gap: 7px; overflow-x: auto; padding-bottom: 2px; }
  .preview-actions::-webkit-scrollbar { display: none; }
  .clear-btn, .undo-btn, .pill-action {
    background: var(--surface); border: 1px solid var(--border); color: var(--text);
    font-size: 12px; font-weight: 600; padding: 8px 13px; border-radius: 999px; cursor: pointer; white-space: nowrap;
  }
  .pill-action.primary { background: var(--ink); color: var(--on-ink); border-color: var(--ink); }
  .undo-btn:disabled { opacity: 0.35; cursor: not-allowed; }

  #grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; }
  @media (max-width: 360px) { #grid { grid-template-columns: repeat(2, 1fr); } }
  .thumb {
    position: relative; border-radius: 16px; overflow: hidden; aspect-ratio: 3 / 4;
    background: var(--surface); border: 1.5px solid var(--border); cursor: grab; box-shadow: var(--shadow);
    animation: popIn .38s var(--spring) both;
  }
  @keyframes popIn { from { opacity: 0; transform: scale(0.84); } to { opacity: 1; transform: none; } }
  .thumb.selected-thumb { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent); }
  .thumb.dragging { opacity: 0.4; transform: scale(0.95); }
  .thumb img { width: 100%; height: 100%; object-fit: cover; display: block; background: #fff; }
  .thumb-select { position: absolute; top: 7px; left: 7px; width: 20px; height: 20px; cursor: pointer; accent-color: var(--accent); z-index: 10; }
  .thumb .del { position: absolute; top: 6px; right: 6px; background: rgba(10, 10, 12, 0.72); color: #fff; border: none; width: 24px; height: 24px; border-radius: 50%; font-size: 12px; cursor: pointer; display: grid; place-items: center; z-index: 10; }
  .thumb-actions { position: absolute; bottom: 0; left: 0; right: 0; display: flex; justify-content: flex-end; gap: 4px; padding: 20px 6px 6px; background: linear-gradient(transparent, rgba(0, 0, 0, 0.74)); z-index: 10; }
  .thumb-action-btn { background: rgba(255, 255, 255, 0.2); border: none; color: #fff; width: 26px; height: 26px; border-radius: 8px; cursor: pointer; font-size: 12px; display: grid; place-items: center; }
  .page-badge { position: absolute; bottom: 7px; left: 7px; background: rgba(10, 10, 12, 0.78); color: #fff; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 999px; z-index: 11; }
  .thumb.fly { animation: flyAway .8s cubic-bezier(.6,-0.2,.4,1) var(--d,0s) forwards !important; }
  @keyframes flyAway { 0% { transform: none; opacity: 1; } 100% { transform: translate(var(--tx,0), -50vh) scale(.15) rotate(240deg); opacity: 0; } }

  #info-bar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; font-size: 11.5px; color: var(--muted); background: var(--surface); border: 1px solid var(--border); padding: 10px 14px; border-radius: 14px; }
  #info-bar b { color: var(--text); font-weight: 600; }

  #gen-btn {
    width: 100%; height: 54px; background: var(--ink); color: var(--on-ink); border: none; border-radius: 999px;
    font-size: 15px; font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center;
    gap: 8px; box-shadow: var(--shadow-md); position: relative; overflow: hidden;
  }
  #gen-btn::after { content: ''; position: absolute; top: 0; bottom: 0; width: 70px; left: -100px; background: linear-gradient(90deg, transparent, rgba(128,128,128,.38), transparent); transform: skewX(-20deg); animation: sweep 3.6s ease-in-out infinite; }
  @keyframes sweep { 0%,45% { left: -100px; } 100% { left: 125%; } }
  #gen-btn:active { transform: scale(0.975); }
  #gen-btn:disabled { opacity: 0.45; cursor: not-allowed; }
  #gen-btn:disabled::after { display: none; }

  #progress-wrap { display: none; width: 100%; }
  .prog-track { height: 6px; background: var(--border); border-radius: 999px; overflow: hidden; }
  #prog-bar { height: 100%; width: 0%; border-radius: 999px; background: var(--accent); transition: width .25s var(--ease); }
  #prog-label { font-size: 12px; color: var(--muted); margin-top: 7px; text-align: center; }

  #result { background: var(--surface); border: 1.5px solid var(--green); border-radius: 22px; padding: 16px; display: none; flex-direction: column; gap: 12px; box-shadow: var(--shadow-md); animation: resultPop .45s var(--spring) both; }
  @keyframes resultPop { from { opacity: 0; transform: scale(0.92) translateY(14px); } to { opacity: 1; transform: none; } }
  .result-top { display: flex; align-items: center; gap: 12px; }
  .res-badge-ico { width: 40px; height: 40px; border-radius: 12px; background: rgba(77, 184, 135, 0.14); color: var(--green); display: grid; place-items: center; flex-shrink: 0; }
  .res-info { flex: 1; min-width: 0; }
  .res-name { font-weight: 700; font-size: 14px; color: var(--text); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .res-size { font-size: 12px; color: var(--green); font-weight: 600; margin-top: 2px; }
  .result-btns { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
  #dl-btn, #share-btn { height: 44px; border-radius: 999px; font-weight: 600; font-size: 13.5px; display: flex; align-items: center; justify-content: center; gap: 6px; cursor: pointer; text-decoration: none; }
  #dl-btn { background: var(--ink); color: var(--on-ink); border: none; }
  #share-btn { background: var(--surface-sunken); color: var(--text); border: 1px solid var(--border); }

  #empty { text-align: center; padding: 46px 20px; background: var(--surface); border: 1px solid var(--border); border-radius: 24px; display: flex; flex-direction: column; align-items: center; gap: 10px; }
  .empty-ico { width: 56px; height: 56px; border-radius: 18px; background: var(--surface-sunken); border: 1px solid var(--border); display: grid; place-items: center; color: var(--muted); }
  #empty h3 { font-size: 16px; font-weight: 700; color: var(--text); }
  #empty p { font-size: 12.5px; color: var(--muted); line-height: 1.5; max-width: 260px; }
  .empty-actions { display: flex; gap: 8px; margin-top: 6px; }

  .pref-group { background: var(--surface); border: 1px solid var(--border); border-radius: 22px; overflow: hidden; box-shadow: var(--shadow); }
  .pref-row { padding: 13px 16px; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; }
  .pref-row:last-child { border-bottom: none; }
  .pref-row.inline { flex-direction: row; align-items: center; justify-content: space-between; gap: 12px; }
  .pref-row.clickable { cursor: pointer; }
  .pref-row.clickable:active { background: var(--surface-sunken); }
  .pref-grid-2 { display: grid; grid-template-columns: 1fr 1fr; border-bottom: 1px solid var(--border); }
  .pref-grid-2 .pref-row { border-bottom: none; }
  .pref-grid-2 .pref-row:first-child { border-right: 1px solid var(--border); }
  .setting-label { font-size: 12px; font-weight: 600; color: var(--muted); display: flex; justify-content: space-between; align-items: center; }
  .pref-title { font-size: 14px; font-weight: 600; color: var(--text); }
  .pref-sub { font-size: 11.5px; color: var(--muted); margin-top: 2px; }
  .quality-val { color: var(--accent); font-weight: 700; font-variant-numeric: tabular-nums; }

  select, input[type=text] { width: 100%; height: 40px; background: var(--surface-sunken); border: 1px solid var(--border); color: var(--text); border-radius: 12px; padding: 0 12px; font-family: inherit; font-size: 13px; outline: none; }
  select:focus, input[type=text]:focus { border-color: var(--accent); }
  input[type=range] { -webkit-appearance: none; appearance: none; width: 100%; height: 5px; background: var(--border); border-radius: 999px; cursor: pointer; outline: none; margin: 6px 0 2px; }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance: none; width: 22px; height: 22px; border-radius: 50%; background: var(--ink); border: 3px solid var(--surface); box-shadow: 0 2px 6px rgba(0,0,0,.35); }

  .toggle { position: relative; display: inline-block; width: 46px; height: 26px; flex-shrink: 0; }
  .toggle input { opacity: 0; width: 0; height: 0; }
  .slider-tog { position: absolute; cursor: pointer; inset: 0; background: var(--border); border-radius: 999px; transition: background .25s; }
  .slider-tog:before { position: absolute; content: ""; height: 20px; width: 20px; left: 3px; bottom: 3px; background: var(--surface); border-radius: 50%; transition: transform .3s var(--spring); box-shadow: 0 1px 3px rgba(0,0,0,.3); }
  input:checked + .slider-tog { background: var(--ink); }
  input:checked + .slider-tog:before { transform: translateX(20px); background: var(--on-ink); }

  .nup-row { display: flex; gap: 6px; }
  .nup-btn { flex: 1; min-width: 0; background: var(--surface-sunken); border: 1px solid var(--border); border-radius: 12px; padding: 8px 0 6px; cursor: pointer; color: var(--text); font-size: 10.5px; font-weight: 600; display: flex; flex-direction: column; align-items: center; gap: 5px; }
  .nup-btn i { display: grid; gap: 1.5px; width: 18px; height: 18px; }
  .nup-btn i b { background: var(--muted); border-radius: 1.5px; }
  .nup-btn.active { background: var(--ink); color: var(--on-ink); border-color: var(--ink); }
  .nup-btn.active i b { background: var(--on-ink); }

  .bottom-nav {
    position: fixed; bottom: 0; left: 50%; transform: translateX(-50%); width: 100%; max-width: 540px;
    height: calc(var(--bnav-h) + var(--safe-bot)); padding: 6px 10px calc(6px + var(--safe-bot));
    background: var(--bar-bg); backdrop-filter: blur(22px); -webkit-backdrop-filter: blur(22px);
    border-top: 1px solid var(--border); display: grid; grid-template-columns: repeat(4, 1fr); z-index: 40;
  }
  .bnav-item { background: none; border: none; color: var(--muted); display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; cursor: pointer; position: relative; }
  .bnav-pill { width: 54px; height: 30px; border-radius: 999px; display: grid; place-items: center; position: relative; transition: background .25s var(--ease), transform .25s var(--spring); }
  .bnav-pill svg { width: 20px; height: 20px; stroke-width: 1.9; }
  .bnav-label { font-size: 11px; font-weight: 600; }
  .bnav-item.active { color: var(--text); }
  .bnav-item.active .bnav-pill { background: var(--accent-soft); color: var(--accent); transform: scale(1.04); }
  .bnav-item:active .bnav-pill { transform: scale(0.92); }
  .bnav-badge { position: absolute; top: 1px; right: 8px; min-width: 17px; height: 17px; padding: 0 4px; border-radius: 999px; background: var(--accent); color: var(--bg); font-size: 10px; font-weight: 700; display: none; align-items: center; justify-content: center; }

  .modal-overlay {
    position: fixed; inset: 0; background: var(--sheet-scrim); z-index: 100; display: none;
    flex-direction: column; align-items: center; justify-content: flex-end; backdrop-filter: blur(4px);
  }
  @media (min-width: 600px) { .modal-overlay { justify-content: center; padding: 20px; } }
  .modal-box {
    background: var(--surface); border-radius: 28px 28px 0 0; width: 100%; max-width: 540px;
    padding: 10px 20px calc(20px + var(--safe-bot)); display: flex; flex-direction: column; gap: 14px;
    box-shadow: var(--shadow-md); border-top: 1px solid var(--border); max-height: 90vh; overflow-y: auto;
    animation: sheetUp .34s var(--ease) both;
  }
  @media (min-width: 600px) { .modal-box { border-radius: 26px; border: 1px solid var(--border); padding: 16px 22px 22px; } }
  @keyframes sheetUp { from { opacity: 0; transform: translateY(48px); } to { opacity: 1; transform: none; } }
  .sheet-handle { width: 38px; height: 4px; border-radius: 999px; background: var(--border-strong); margin: 2px auto 4px; flex-shrink: 0; }
  .modal-box h2 { font-family: 'Fraunces', serif; font-size: 20px; font-weight: 600; color: var(--text); }
  .modal-sub { font-size: 12.5px; color: var(--muted); margin-top: -8px; line-height: 1.45; }

  .modal-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 2px; }
  .btn-cancel { height: 44px; background: var(--surface-sunken); color: var(--text); border: 1px solid var(--border); padding: 0 18px; border-radius: 999px; cursor: pointer; font-size: 13.5px; font-weight: 600; }
  .btn-primary { height: 44px; background: var(--ink); color: var(--on-ink); border: none; padding: 0 20px; border-radius: 999px; cursor: pointer; font-weight: 700; font-size: 13.5px; display: inline-flex; align-items: center; justify-content: center; gap: 6px; }
  .btn-primary:disabled { opacity: 0.45; cursor: not-allowed; }

  #camera-modal { justify-content: center; padding: var(--safe-top) 12px calc(16px + var(--safe-bot)); background: #000; }
  #video-stream { flex: 1; width: 100%; max-height: calc(100vh - 140px); object-fit: cover; background: #111; border-radius: 22px; }
  .cam-controls { height: 96px; width: 100%; display: flex; align-items: center; justify-content: space-around; margin-top: 10px; }
  .cam-close { background: rgba(255,255,255,.15); border: none; color: #fff; font-size: 14px; font-weight: 600; padding: 10px 18px; border-radius: 999px; cursor: pointer; }
  .cam-snap { width: 68px; height: 68px; border-radius: 50%; background: #fff; border: 4px solid rgba(255,255,255,.4); cursor: pointer; }
  .cam-count { color: #fff; font-weight: 700; font-size: 16px; width: 58px; text-align: center; }
  #cam-flash { position: absolute; inset: 0; background: #fff; opacity: 0; pointer-events: none; transition: opacity .08s; }

  .tb-title-row { display: flex; gap: 8px; }
  .tb-title-input { flex: 1; font-weight: 600; }
  #text-input-area { width: 100%; height: 190px; min-height: 120px; max-height: 44vh; background: var(--surface-sunken); color: var(--text); border: 1px solid var(--border); border-radius: 16px; padding: 13px; font-family: inherit; font-size: 14px; line-height: 1.5; resize: vertical; outline: none; }
  .text-toolbar { display: flex; gap: 7px; flex-wrap: wrap; align-items: center; }
  .text-toolbar select { width: auto; height: 34px; padding: 0 8px; font-size: 12px; border-radius: 10px; }
  .text-toolbar .tb-group { display: flex; gap: 4px; align-items: center; }
  .tb-btn { background: var(--surface-sunken); border: 1px solid var(--border); color: var(--text); width: 34px; height: 34px; border-radius: 10px; cursor: pointer; font-size: 12px; font-weight: 600; display: grid; place-items: center; }
  .tb-btn.active { border-color: var(--ink); background: var(--ink); color: var(--on-ink); }
  .tb-color-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
  .tb-color { width: 22px; height: 22px; border-radius: 50%; cursor: pointer; border: 2px solid var(--border); }
  .tb-color.active { border-color: var(--accent); transform: scale(1.15); }
  .tb-divider { width: 1px; height: 18px; background: var(--border); }
  .fmt-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .fmt-btn { background: var(--surface-sunken); border: 1px solid var(--border); color: var(--text); border-radius: 999px; padding: 6px 11px; font-size: 11.5px; font-weight: 600; cursor: pointer; white-space: nowrap; }
  .fmt-btn.active { background: var(--ink); color: var(--on-ink); border-color: var(--ink); }
  #note-lang { width: auto; height: 32px; padding: 0 8px; font-size: 11.5px; display: none; }
  #note-preview { display: none; height: 42vh; min-height: 200px; overflow: auto; border: 1px solid var(--border); border-radius: 14px; background: var(--surface-sunken); }
  #note-preview-inner { position: relative; margin: 0 auto; overflow: hidden; }
  #note-preview-frame { width: 794px; border: 0; transform-origin: 0 0; display: block; }

  .crop-container { width: 100%; height: 55vh; background: #111; border-radius: 16px; overflow: hidden; }
  .modal-name-input { width: 100%; }

  #compress-drop, #compress-video-drop, .gt-drop {
    background: var(--surface-sunken); border: 1.5px dashed var(--border-strong); border-radius: 18px;
    padding: 26px 16px; text-align: center; cursor: pointer; position: relative;
    display: flex; flex-direction: column; align-items: center; gap: 6px;
  }
  #compress-drop input, #compress-video-drop input, .gt-drop input { position: absolute; inset: 0; opacity: 0; cursor: pointer; width: 100%; height: 100%; }
  #compress-drop .drop-title, #compress-video-drop .drop-title, .gt-drop .drop-title { color: var(--text); font-size: 14px; }
  #compress-drop .drop-sub, #compress-video-drop .drop-sub, .gt-drop .drop-sub { color: var(--muted); font-size: 12px; opacity: 1; }
  .compress-file-row { display: flex; align-items: center; gap: 12px; background: var(--surface-sunken); border: 1px solid var(--border); border-radius: 16px; padding: 12px 14px; }
  .compress-file-icon { font-size: 20px; filter: grayscale(1); }
  .compress-file-info { flex: 1; min-width: 0; }
  .compress-file-name { font-weight: 600; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .compress-file-size { font-size: 11.5px; color: var(--muted); margin-top: 2px; }
  .compress-remove { background: none; border: none; color: var(--muted); cursor: pointer; font-size: 16px; padding: 6px; }
  .compress-level-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
  .compress-level-btn { background: var(--surface-sunken); border: 1px solid var(--border); border-radius: 14px; padding: 11px 6px; text-align: center; cursor: pointer; }
  .compress-level-btn .lvl-name { font-size: 12.5px; font-weight: 700; }
  .compress-level-btn .lvl-desc { font-size: 10px; color: var(--muted); margin-top: 2px; }
  .compress-level-btn.active { border-color: var(--ink); background: var(--ink); color: var(--on-ink); }
  .compress-level-btn.active .lvl-desc { color: var(--on-ink); opacity: 0.72; }
  .compress-result { display: none; flex-direction: column; gap: 12px; }
  .compress-result-stats { display: flex; align-items: center; justify-content: space-between; background: var(--surface-sunken); border-radius: 16px; padding: 14px; }
  .compress-stat { text-align: center; flex: 1; }
  .compress-stat .num { font-family: 'Fraunces', serif; font-size: 20px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .compress-stat .lbl { font-size: 10.5px; color: var(--muted); margin-top: 2px; }
  .compress-stat.saved .num { color: var(--green); }
  .compress-arrow { color: var(--muted); font-size: 16px; }

  .gt-opt { display: flex; flex-direction: column; gap: 7px; }
  .gt-seg { display: flex; gap: 6px; flex-wrap: wrap; }
  .gt-seg button { flex: 1; min-width: 60px; background: var(--surface-sunken); border: 1px solid var(--border); color: var(--text); border-radius: 12px; padding: 10px 8px; font-size: 12px; font-weight: 600; cursor: pointer; }
  .gt-seg button.active { background: var(--ink); color: var(--on-ink); border-color: var(--ink); }
  #gt-res { display: none; flex-direction: column; gap: 10px; }
  #gt-res .big-num { font-family: 'Fraunces', serif; font-size: 26px; font-weight: 600; text-align: center; }
  #gt-res .lbl { font-size: 11px; color: var(--muted); text-align: center; }

  #lightbox { position: fixed; inset: 0; background: rgba(0,0,0,.96); z-index: 200; display: none; flex-direction: column; align-items: center; justify-content: center; }
  #lightbox img { max-width: 94vw; max-height: 82vh; border-radius: 14px; object-fit: contain; }
  #lightbox-close { position: absolute; top: calc(14px + var(--safe-top)); right: 16px; color: #fff; font-size: 20px; cursor: pointer; background: rgba(255,255,255,.16); border: none; width: 40px; height: 40px; border-radius: 50%; display: grid; place-items: center; }
  #lightbox-nav { position: absolute; bottom: calc(22px + var(--safe-bot)); display: flex; gap: 14px; align-items: center; }
  .lb-nav-btn { background: rgba(255,255,255,.16); border: none; color: #fff; width: 42px; height: 42px; border-radius: 50%; font-size: 20px; cursor: pointer; display: grid; place-items: center; }
  #lightbox-label { color: rgba(255,255,255,.8); font-size: 13px; font-weight: 600; min-width: 60px; text-align: center; }

  #toast {
    position: fixed; bottom: calc(var(--bnav-h) + var(--safe-bot) + 14px); left: 50%;
    transform: translateX(-50%) translateY(16px) scale(0.95); background: var(--ink); color: var(--on-ink);
    padding: 11px 18px; border-radius: 999px; font-size: 13px; font-weight: 600; opacity: 0; pointer-events: none;
    transition: opacity .22s var(--ease), transform .3s var(--spring); z-index: 300; box-shadow: var(--shadow-md);
    max-width: calc(100vw - 32px); white-space: nowrap;
  }
  #toast.show { opacity: 1; transform: translateX(-50%) translateY(0) scale(1); }
  #confetti { position: fixed; inset: 0; z-index: 400; pointer-events: none; }
  .rip-host { position: relative; overflow: hidden; }
  .ripple { position: absolute; border-radius: 50%; background: rgba(128,128,128,.28); transform: scale(0); animation: ripple .65s ease-out forwards; pointer-events: none; z-index: 5; }
  @keyframes ripple { to { transform: scale(1); opacity: 0; } }
  .about-hero { display: flex; align-items: center; gap: 14px; padding: 14px; background: var(--surface-sunken); border: 1px solid var(--border); border-radius: 18px; }
  .about-badge { display: inline-block; font-size: 11px; font-weight: 600; color: var(--accent); background: var(--accent-soft); padding: 3px 9px; border-radius: 999px; margin-top: 4px; }
</style>

<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/tesseract.js/5.0.4/tesseract.min.js" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/cropperjs/1.6.1/cropper.min.js" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js" crossorigin="anonymous"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jszip/3.10.1/jszip.min.js" crossorigin="anonymous"></script>
<script src="/vendor/ffmpeg/ffmpeg.min.js"></script>
</head>
<body>
<div id="aurora"></div>
<canvas id="confetti"></canvas>

<div class="app-shell">
  <header class="app-topbar">
    <div class="app-brand-mark" aria-hidden="true">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9.5 13h5M9.5 16.5h3.5"/>
      </svg>
    </div>
    <div class="topbar-titles">
      <div class="topbar-title-row">
        <h1 class="header-title">Pexi<span>PDF</span></h1>
        <span class="xcluice-tag">by Xcluice</span>
      </div>
      <div class="header-sub"><span id="tagline" class="tagline">Images &amp; PDFs to PDF</span></div>
    </div>
    <div class="topbar-actions">
      <button type="button" class="top-pill" id="top-pages-pill" title="Open Pages Workspace"><span class="dot"></span><span id="top-pages-num">0 pages</span></button>
      <button type="button" class="icon-btn" id="theme-toggle" title="Toggle theme">☀</button>
      <button type="button" class="icon-btn" id="about-btn" title="About PexiPDF by Xcluice">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
      </button>
    </div>
  </header>

  <main id="app-scroll">
    <section class="app-screen active" data-screen="home">
      <div class="section-row"><span class="section-label">Studio</span><span class="offline-pill">100% OFFLINE</span></div>
      <div id="dropzone" class="hero-card rip-host">
        <input type="file" id="file-input" accept="image/*,application/pdf" multiple>
        <span class="ring"></span><span class="ring r2"></span>
        <div class="hero-top">
          <span class="drop-icon"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4M7 9l5-5 5 5M4 15v4h16v-4"/></svg></span>
          <span class="hero-chip">JPG · PNG · PDF</span>
        </div>
        <div class="hero-copy">
          <div class="drop-title">Create or Merge PDF</div>
          <div class="drop-sub">Tap to browse photos &amp; documents on your device</div>
        </div>
      </div>

      <div id="home-workspace-banner" class="rip-host" role="button">
        <div class="ws-icon"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 10h8M8 14h5"/></svg></div>
        <div class="ws-info"><div class="ws-title" id="home-ws-count">0 pages in workspace</div><div class="ws-sub">Reorder, crop, OCR &amp; export your PDF</div></div>
        <span class="ws-go">Open ›</span>
      </div>

      <div class="section-row"><span class="section-label">Quick Actions</span></div>
      <div class="tool-grid" id="tool-grid">
        <button type="button" class="tool tool-camera" id="btn-camera">
          <span class="t-ico-wrap"><svg class="t-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg></span>
          <div><div class="t-name">Camera Scan</div><div class="t-desc">Capture pages live</div></div>
        </button>
        <button type="button" class="tool tool-text" id="btn-text">
          <span class="t-ico-wrap"><svg class="t-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h4L19 9l-4-4L4 16z"/><path d="M13 7l4 4"/></svg></span>
          <div><div class="t-name">Rich Note</div><div class="t-desc">Text · MD · Code · SVG</div></div>
        </button>
        <button type="button" class="tool tool-pdfc" id="btn-compress">
          <span class="t-ico-wrap"><svg class="t-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/></svg></span>
          <div><div class="t-name">Compress PDF</div><div class="t-desc">Shrink file size fast</div></div>
        </button>
        <button type="button" class="tool tool-vidc" id="btn-compress-video">
          <span class="t-ico-wrap"><svg class="t-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9.5v5l4.5-2.5z"/></svg></span>
          <div><div class="t-name">Compress Video</div><div class="t-desc">Smaller, crisp quality</div></div>
        </button>
      </div>

      <div class="marquee"><div class="track" id="marq-track"></div></div>
    </section>

    <section class="app-screen" data-screen="pages">
      <div id="est-size-bar">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 20V10M12 20V4M6 20v-6"/></svg>
        <span>Est. PDF size: <span id="est-size-val">—</span></span>
        <span style="margin-left:auto;font-size:10.5px;">approx.</span>
      </div>

      <div id="preview-section">
        <div class="preview-header">
          <h2 class="pages-title">Pages · <span id="count">0</span></h2>
          <button type="button" class="pill-action primary" id="pages-add-btn">+ Add</button>
        </div>
        <div class="preview-actions">
          <button type="button" class="clear-btn" id="select-all-btn">☑ Select All</button>
          <button type="button" class="clear-btn" id="reverse-btn">⇅ Reverse</button>
          <button type="button" class="undo-btn" id="undo-btn" disabled>↩ Undo</button>
          <button type="button" class="clear-btn" id="clear-all-btn">✕ Clear</button>
        </div>
        <div id="grid"></div>
        <div id="info-bar">
          <span>Pages: <b id="ib-pages">0</b></span>
          <span>Size: <b id="ib-size">0 KB</b></span>
          <span style="margin-left:auto;font-size:11px;">Tap checkbox to split</span>
        </div>
        <button type="button" id="gen-btn">Generate PDF</button>
        <div id="progress-wrap"><div class="prog-track"><div id="prog-bar"></div></div><div id="prog-label">Processing…</div></div>
        <div id="result">
          <div class="result-top">
            <div class="res-badge-ico"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg></div>
            <div class="res-info"><div class="res-name" id="res-name">output.pdf</div><div class="res-size" id="res-size"></div></div>
          </div>
          <div class="result-btns"><a id="dl-btn">⬇ Save PDF</a><button type="button" id="share-btn">⬆ Share</button></div>
        </div>
      </div>

      <div id="empty">
        <div class="empty-ico"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 13h6M12 10v6"/></svg></div>
        <h3>No pages yet</h3>
        <p>Add images or PDFs, scan with your camera, or write a formatted note to build your PDF.</p>
        <div class="empty-actions">
          <button type="button" class="btn-primary" id="empty-browse-btn">Browse Files</button>
          <button type="button" class="btn-cancel" id="empty-cam-btn">Camera</button>
        </div>
      </div>
    </section>

    <section class="app-screen" data-screen="tools">
      <div class="section-row"><span class="section-label">PDF Utilities</span></div>
      <div class="android-group" id="tool-grid-more">
        <button type="button" class="tool-row" data-trigger="btn-compress">
          <span class="tr-ico" style="--c1:#2F4ACB"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M9 4v5H4M15 4v5h5M9 20v-5H4M15 20v-5h5"/></svg></span>
          <span class="tr-body"><span class="tr-title">Compress PDF</span><span class="tr-sub">Light, balanced, or strong offline compression</span></span>
          <span class="tr-chev">›</span>
        </button>
        <button type="button" class="tool-row" data-gt="pdf2img">
          <span class="tr-ico" style="--c1:#C98A2B"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><polyline points="8 18 11 14.5 13.5 17 15 15.5 16.5 18"/></svg></span>
          <span class="tr-body"><span class="tr-title">PDF → Images <span class="tag-pill">ZIP</span></span><span class="tr-sub">Export every PDF page as crisp PNG or JPG</span></span>
          <span class="tr-chev">›</span>
        </button>
        <button type="button" class="tool-row" data-gt="pdf2txt">
          <span class="tr-ico" style="--c1:#2F4ACB"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9 12h6M9 15h6M9 18h4"/></svg></span>
          <span class="tr-body"><span class="tr-title">PDF → Text</span><span class="tr-sub">Extract clean plain text from any PDF</span></span>
          <span class="tr-chev">›</span>
        </button>
        <button type="button" class="tool-row" data-gt="extract">
          <span class="tr-ico" style="--c1:#2E8B62"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><circle cx="6" cy="6" r="2.5"/><circle cx="6" cy="18" r="2.5"/><path d="M8 7.5L20 18M8 16.5L20 6"/></svg></span>
          <span class="tr-body"><span class="tr-title">Extract Pages</span><span class="tr-sub">Split ranges like 1-3, 7 into a new PDF</span></span>
          <span class="tr-chev">›</span>
        </button>
      </div>

      <div class="section-row"><span class="section-label">Image &amp; Video Tools</span></div>
      <div class="android-group">
        <button type="button" class="tool-row" data-gt="imgconv">
          <span class="tr-ico" style="--c1:#C98A2B"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M4 8h14l-3-3M20 16H6l3 3"/></svg></span>
          <span class="tr-body"><span class="tr-title">Image Converter</span><span class="tr-sub">Convert JPG, PNG, WebP and resize</span></span>
          <span class="tr-chev">›</span>
        </button>
        <button type="button" class="tool-row" data-trigger="btn-compress-video">
          <span class="tr-ico" style="--c1:#C93B3B"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M10 9.5v5l4.5-2.5z"/></svg></span>
          <span class="tr-body"><span class="tr-title">Compress Video</span><span class="tr-sub">Shrink MP4 videos without visible loss</span></span>
          <span class="tr-chev">›</span>
        </button>
        <button type="button" class="tool-row" data-gt="vid2mp3">
          <span class="tr-ico" style="--c1:#8A5BC9"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18V5l11-2v13"/><circle cx="6.5" cy="18" r="2.5"/><circle cx="17.5" cy="16" r="2.5"/></svg></span>
          <span class="tr-body"><span class="tr-title">Video → MP3</span><span class="tr-sub">Extract audio track directly on device</span></span>
          <span class="tr-chev">›</span>
        </button>
        <button type="button" class="tool-row" data-gt="vid2gif">
          <span class="tr-ico" style="--c1:#2F7FA8"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/></svg></span>
          <span class="tr-body"><span class="tr-title">Video → GIF</span><span class="tr-sub">Create compact looping GIF clips</span></span>
          <span class="tr-chev">›</span>
        </button>
      </div>
    </section>

    <section class="app-screen" data-screen="settings">
      <div class="section-row"><span class="section-label">PDF Output</span></div>
      <div class="pref-group">
        <div class="pref-row"><div class="setting-label">File name</div><input type="text" id="file-name" placeholder="document"></div>
        <div class="pref-grid-2">
          <div class="pref-row"><div class="setting-label">Page size</div><select id="page-size"><option value="A4">A4</option><option value="A3">A3</option><option value="Letter">Letter</option><option value="fit">Fit to image</option></select></div>
          <div class="pref-row"><div class="setting-label">Orientation</div><select id="orientation"><option value="portrait">Portrait</option><option value="landscape">Landscape</option><option value="auto">Auto</option></select></div>
        </div>
        <div class="pref-grid-2">
          <div class="pref-row"><div class="setting-label">Scanner filter</div><select id="img-filter"><option value="color">Original Color</option><option value="bw">B&amp;W (Magic)</option><option value="gray">Grayscale</option></select></div>
          <div class="pref-row"><div class="setting-label">Margins</div><select id="margins"><option value="0">None</option><option value="20">Small (7mm)</option><option value="40" selected>Normal (14mm)</option><option value="60">Large (21mm)</option></select></div>
        </div>
        <div class="pref-row">
          <div class="setting-label"><span>Image quality</span><span class="quality-val" id="q-val">60%</span></div>
          <input type="range" id="quality" min="10" max="95" value="60">
        </div>
      </div>

      <div class="section-row"><span class="section-label">Layout &amp; Security</span></div>
      <div class="pref-group">
        <div class="pref-row">
          <div class="setting-label"><span>Pages per sheet (N-up)</span><span class="quality-val" id="nup-val">1</span></div>
          <div class="nup-row" id="nup-row">
            <button type="button" class="nup-btn active" data-n="1"><i style="grid-template-columns:1fr"><b></b></i>1</button>
            <button type="button" class="nup-btn" data-n="2"><i style="grid-template-columns:1fr 1fr"><b></b><b></b></i>2-up</button>
            <button type="button" class="nup-btn" data-n="4"><i style="grid-template-columns:1fr 1fr"><b></b><b></b><b></b><b></b></i>4-up</button>
            <button type="button" class="nup-btn" data-n="6"><i style="grid-template-columns:1fr 1fr 1fr"><b></b><b></b><b></b><b></b><b></b><b></b></i>6-up</button>
            <button type="button" class="nup-btn" data-n="9"><i style="grid-template-columns:1fr 1fr 1fr"><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b><b></b></i>9-up</button>
          </div>
        </div>
        <div class="pref-grid-2">
          <div class="pref-row"><div class="setting-label">Watermark</div><input type="text" id="watermark-text" placeholder="Optional text"></div>
          <div class="pref-row"><div class="setting-label">Password lock</div><input type="text" id="pdf-password" placeholder="Optional lock" autocomplete="off"></div>
        </div>
        <div class="pref-row inline"><div><div class="pref-title">Page numbers</div><div class="pref-sub">Stamp page count in footer</div></div><label class="toggle"><input type="checkbox" id="page-numbers"><span class="slider-tog"></span></label></div>
        <div class="pref-row inline"><div><div class="pref-title">Compress output</div><div class="pref-sub">Optimize PDF streams automatically</div></div><label class="toggle"><input type="checkbox" id="compress" checked><span class="slider-tog"></span></label></div>
      </div>

      <div class="section-row"><span class="section-label">App &amp; Appearance</span></div>
      <div class="pref-group">
        <div class="pref-row inline"><div><div class="pref-title">Dark mode</div><div class="pref-sub">OLED monochrome dark surface</div></div><label class="toggle"><input type="checkbox" id="settings-dark-toggle" checked><span class="slider-tog"></span></label></div>
        <div class="pref-row inline clickable" id="settings-update-row" role="button"><div><div class="pref-title">Check for updates</div><div class="pref-sub">GitHub Releases · Xcluice/pexipdf</div></div><span class="quality-val" id="app-version-label">Web</span></div>
        <div class="pref-row inline clickable" id="settings-about-row" role="button"><div><div class="pref-title">About PexiPDF</div><div class="pref-sub">Built by Xcluice · 100% private &amp; offline</div></div><span class="tr-chev">›</span></div>
      </div>
    </section>
  </main>

  <nav class="bottom-nav" aria-label="Main navigation">
    <button type="button" class="bnav-item active" data-tab="home" aria-selected="true">
      <span class="bnav-pill"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M3 10.5L12 3l9 7.5V20a1 1 0 0 1-1 1h-5.5v-6.5h-5V21H4a1 1 0 0 1-1-1z"/></svg></span>
      <span class="bnav-label">Home</span>
    </button>
    <button type="button" class="bnav-item" data-tab="pages" aria-selected="false">
      <span class="bnav-pill"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h8M8 17h5"/></svg><span class="bnav-badge" id="nav-pages-badge">0</span></span>
      <span class="bnav-label">Pages</span>
    </button>
    <button type="button" class="bnav-item" data-tab="tools" aria-selected="false">
      <span class="bnav-pill"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="3" width="7.5" height="7.5" rx="2"/><rect x="3" y="13.5" width="7.5" height="7.5" rx="2"/><rect x="13.5" y="13.5" width="7.5" height="7.5" rx="2"/></svg></span>
      <span class="bnav-label">Tools</span>
    </button>
    <button type="button" class="bnav-item" data-tab="settings" aria-selected="false">
      <span class="bnav-pill"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3.2"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg></span>
      <span class="bnav-label">Settings</span>
    </button>
  </nav>
</div>

<div id="camera-modal" class="modal-overlay">
  <video id="video-stream" autoplay playsinline></video>
  <div id="cam-flash"></div>
  <div class="cam-controls">
    <button type="button" class="cam-close" id="cam-close-btn">Done</button>
    <button type="button" class="cam-snap" id="cam-snap-btn" aria-label="Capture page"></button>
    <div class="cam-count" id="cam-counter">0</div>
  </div>
</div>

<div id="text-modal" class="modal-overlay">
  <div class="modal-box">
    <div class="sheet-handle"></div>
    <h2>Rich Note to PDF</h2>
    <div class="tb-title-row"><input type="text" class="tb-title-input" id="note-title" placeholder="Title (optional)…"></div>
    <div class="text-toolbar">
      <div class="tb-group"><select id="note-font-size"><option value="12">12px</option><option value="14" selected>14px</option><option value="16">16px</option><option value="18">18px</option><option value="22">22px</option><option value="28">28px</option><option value="36">36px</option></select></div>
      <div class="tb-group"><select id="note-font"><option value="Inter, Arial, sans-serif">Sans-serif</option><option value="Georgia, 'Times New Roman', serif">Serif</option><option value="Fraunces, Georgia, serif">Elegant</option><option value="'Courier New', monospace">Mono</option><option value="'Segoe Print', 'Comic Sans MS', cursive">Handwritten</option></select></div>
      <div class="tb-divider"></div>
      <div class="tb-group"><button type="button" class="tb-btn" id="tb-bold"><b>B</b></button><button type="button" class="tb-btn" id="tb-italic"><i>I</i></button><button type="button" class="tb-btn" id="tb-underline"><u>U</u></button></div>
      <div class="tb-divider"></div>
      <div class="tb-group">
        <button type="button" class="tb-btn" id="tb-left"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M1 3h12M1 7h8M1 11h10"/></svg></button>
        <button type="button" class="tb-btn" id="tb-center"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M1 3h12M3 7h8M2 11h10"/></svg></button>
        <button type="button" class="tb-btn" id="tb-right"><svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M1 3h12M5 7h8M3 11h10"/></svg></button>
      </div>
      <div class="tb-color-row">
        <div class="tb-color" data-color="#ffffff" style="background:#ffffff;"></div><div class="tb-color" data-color="#FFF9E6" style="background:#FFF9E6;"></div><div class="tb-color" data-color="#F6E9CC" style="background:#F6E9CC;"></div><div class="tb-color" data-color="#EAF5EE" style="background:#EAF5EE;"></div><div class="tb-color" data-color="#FDE7F1" style="background:#FDE7F1;"></div><div class="tb-color" data-color="#E3F2FF" style="background:#E3F2FF;"></div><div class="tb-color" data-color="#EFEFEF" style="background:#EFEFEF;"></div><div class="tb-color" data-color="#111111" style="background:#111111;"></div>
      </div>
    </div>
    <div class="fmt-row" id="fmt-row">
      <button type="button" class="fmt-btn active" data-fmt="auto">Auto</button>
      <button type="button" class="fmt-btn" data-fmt="text">Text</button>
      <button type="button" class="fmt-btn" data-fmt="md">Markdown</button>
      <button type="button" class="fmt-btn" data-fmt="html">HTML · SVG</button>
      <button type="button" class="fmt-btn" data-fmt="code">Code</button>
      <button type="button" class="fmt-btn" data-fmt="csv">CSV</button>
      <select id="note-lang"><option value="auto">Auto-detect</option><option value="javascript">javascript</option><option value="typescript">typescript</option><option value="python">python</option><option value="java">java</option><option value="kotlin">kotlin</option><option value="c">c</option><option value="cpp">cpp</option><option value="csharp">csharp</option><option value="go">go</option><option value="rust">rust</option><option value="php">php</option><option value="ruby">ruby</option><option value="swift">swift</option><option value="sql">sql</option><option value="bash">bash</option><option value="json">json</option><option value="yaml">yaml</option><option value="xml">xml</option><option value="css">css</option><option value="scss">scss</option><option value="lua">lua</option><option value="r">r</option><option value="perl">perl</option><option value="markdown">markdown</option><option value="diff">diff</option><option value="ini">ini</option></select>
      <button type="button" class="fmt-btn" id="note-preview-btn" style="margin-left:auto;">Preview</button>
      <button type="button" class="fmt-btn" id="note-open-btn">Open</button>
      <input type="file" id="note-file" hidden accept=".md,.markdown,.txt,.html,.htm,.svg,.xml,.csv,.tsv,.json,.js,.mjs,.jsx,.ts,.tsx,.py,.java,.kt,.kts,.c,.h,.cpp,.cc,.cs,.go,.rs,.php,.rb,.swift,.sql,.sh,.bash,.yml,.yaml,.css,.scss,.lua,.r,.pl,.gradle,.toml,.ini,.diff,text/*">
    </div>
    <textarea id="text-input-area" placeholder="Type or paste Markdown, HTML, SVG, code, CSV, or plain text…"></textarea>
    <div id="note-preview"><div id="note-preview-inner"><iframe id="note-preview-frame" sandbox="allow-same-origin" title="Preview"></iframe></div></div>
    <div id="note-meta" style="font-size:11px;color:var(--muted);margin-top:-6px;">Long notes automatically flow onto extra pages</div>
    <div class="modal-actions">
      <button type="button" class="btn-cancel" id="text-clear-btn" style="margin-right:auto;">Clear</button>
      <button type="button" class="btn-cancel" id="text-cancel-btn">Close</button>
      <button type="button" class="btn-primary" id="text-save-btn">Add to PDF</button>
    </div>
  </div>
</div>

<div id="crop-modal" class="modal-overlay">
  <div class="modal-box"><div class="sheet-handle"></div><h2>Crop Page</h2><div class="crop-container"><img id="crop-image" src="" alt="To crop"></div><div class="modal-actions"><button type="button" class="btn-cancel" id="crop-cancel-btn">Cancel</button><button type="button" class="btn-primary" id="crop-confirm-btn">Apply Crop</button></div></div>
</div>

<div id="name-modal" class="modal-overlay">
  <div class="modal-box"><div class="sheet-handle"></div><h2>Name your PDF</h2><input type="text" id="pdf-name-input" class="modal-name-input" placeholder="document" maxlength="120"><div class="modal-actions"><button type="button" class="btn-cancel" id="name-cancel-btn">Cancel</button><button type="button" class="btn-primary" id="name-confirm-btn">Generate PDF</button></div></div>
</div>

<div id="compress-modal" class="modal-overlay">
  <div class="modal-box">
    <div class="sheet-handle"></div>
    <h2>Compress PDF</h2>
    <div class="modal-sub">Shrink an existing PDF directly on your device.</div>
    <div id="compress-empty-state"><div id="compress-drop"><input type="file" id="compress-file-input" accept="application/pdf"><div class="drop-title">Tap to pick a PDF</div><div class="drop-sub">100% offline · nothing leaves your device</div></div></div>
    <div id="compress-file-state" style="display:none;flex-direction:column;gap:14px;">
      <div class="compress-file-row"><span class="compress-file-icon">📄</span><div class="compress-file-info"><div class="compress-file-name" id="compress-file-name">document.pdf</div><div class="compress-file-size" id="compress-file-size">0 KB</div></div><button type="button" class="compress-remove" id="compress-remove-btn">✕</button></div>
      <div><div class="setting-label" style="margin-bottom:8px;">Compression level</div><div class="compress-level-row"><div class="compress-level-btn" data-level="light"><div class="lvl-name">Light</div><div class="lvl-desc">Best quality</div></div><div class="compress-level-btn active" data-level="balanced"><div class="lvl-name">Balanced</div><div class="lvl-desc">~50% smaller</div></div><div class="compress-level-btn" data-level="strong"><div class="lvl-name">Strong</div><div class="lvl-desc">Smallest</div></div></div></div>
      <button type="button" class="btn-primary" id="compress-run-btn" style="width:100%;">Compress PDF</button>
      <div id="compress-progress" style="display:none;"><div class="prog-track"><div id="compress-prog-bar" style="height:100%;background:var(--accent);width:0%;border-radius:999px;"></div></div><div id="compress-prog-label" style="font-size:11.5px;color:var(--muted);margin-top:6px;text-align:center;">Compressing…</div></div>
      <div class="compress-result" id="compress-result">
        <div class="compress-result-stats"><div class="compress-stat"><div class="num" id="compress-before">0 MB</div><div class="lbl">Before</div></div><div class="compress-arrow">→</div><div class="compress-stat"><div class="num" id="compress-after">0 MB</div><div class="lbl">After</div></div><div class="compress-stat saved"><div class="num" id="compress-saved">0%</div><div class="lbl">Saved</div></div></div>
        <div class="modal-actions" style="justify-content:stretch;"><a id="compress-dl-btn" class="btn-primary" style="text-decoration:none;flex:1;">⬇ Save Compressed PDF</a></div>
      </div>
    </div>
    <div class="modal-actions"><button type="button" class="btn-cancel" id="compress-close-btn">Close</button></div>
  </div>
</div>

<div id="compress-video-modal" class="modal-overlay">
  <div class="modal-box">
    <div class="sheet-handle"></div>
    <h2>Compress Video</h2>
    <div class="modal-sub">Re-encode video smaller on-device without visible quality loss.</div>
    <div id="compress-video-empty-state"><div id="compress-video-drop"><input type="file" id="compress-video-file-input" accept="video/*"><div class="drop-title">Tap to pick a video</div><div class="drop-sub">Runs locally · nothing is uploaded</div></div></div>
    <div id="compress-video-file-state" style="display:none;flex-direction:column;gap:14px;">
      <div class="compress-file-row"><span class="compress-file-icon">🎥</span><div class="compress-file-info"><div class="compress-file-name" id="compress-video-file-name">video.mp4</div><div class="compress-file-size" id="compress-video-file-size">0 KB</div></div><button type="button" class="compress-remove" id="compress-video-remove-btn">✕</button></div>
      <div><div class="setting-label" style="margin-bottom:8px;">Compression level</div><div class="compress-level-row"><div class="compress-level-btn compress-video-level-btn" data-level="light"><div class="lvl-name">Light</div><div class="lvl-desc">Lossless look</div></div><div class="compress-level-btn compress-video-level-btn active" data-level="balanced"><div class="lvl-name">Balanced</div><div class="lvl-desc">Big savings</div></div><div class="compress-level-btn compress-video-level-btn" data-level="strong"><div class="lvl-name">Strong</div><div class="lvl-desc">Smallest</div></div></div></div>
      <div style="font-size:11px;color:var(--muted);line-height:1.45;">First run downloads the local video engine (~25 MB, cached after that).</div>
      <button type="button" class="btn-primary" id="compress-video-run-btn" style="width:100%;">Compress Video</button>
      <div id="compress-video-progress" style="display:none;"><div class="prog-track"><div id="compress-video-prog-bar" style="height:100%;background:var(--accent);width:0%;border-radius:999px;"></div></div><div id="compress-video-prog-label" style="font-size:11.5px;color:var(--muted);margin-top:6px;text-align:center;">Compressing…</div></div>
      <div class="compress-result" id="compress-video-result">
        <div class="compress-result-stats"><div class="compress-stat"><div class="num" id="compress-video-before">0 MB</div><div class="lbl">Before</div></div><div class="compress-arrow">→</div><div class="compress-stat"><div class="num" id="compress-video-after">0 MB</div><div class="lbl">After</div></div><div class="compress-stat saved"><div class="num" id="compress-video-saved">0%</div><div class="lbl">Saved</div></div></div>
        <div class="modal-actions" style="justify-content:stretch;"><a id="compress-video-dl-btn" class="btn-primary" style="text-decoration:none;flex:1;">⬇ Save Compressed Video</a></div>
      </div>
    </div>
    <div class="modal-actions"><button type="button" class="btn-cancel" id="compress-video-close-btn">Close</button></div>
  </div>
</div>

<div id="gt-modal" class="modal-overlay">
  <div class="modal-box">
    <div class="sheet-handle"></div>
    <h2 id="gt-title">Tool</h2>
    <div class="modal-sub" id="gt-sub"></div>
    <div id="gt-empty"><div class="gt-drop" id="gt-drop"><input type="file" id="gt-input"><div class="drop-icon" id="gt-ico" style="background:var(--surface);color:var(--text);border-color:var(--border);width:44px;height:44px;font-size:20px;">📄</div><div class="drop-title">Tap to pick a file</div><div class="drop-sub">Runs locally on your device · nothing is uploaded</div></div></div>
    <div id="gt-file" style="display:none;flex-direction:column;gap:14px;">
      <div class="compress-file-row"><span class="compress-file-icon" id="gt-file-ico">📄</span><div class="compress-file-info"><div class="compress-file-name" id="gt-file-name">file</div><div class="compress-file-size" id="gt-file-size"></div></div><button type="button" class="compress-remove" id="gt-remove">✕</button></div>
      <div id="gt-opts" style="display:flex;flex-direction:column;gap:12px;"></div>
      <button type="button" class="btn-primary" id="gt-run" style="width:100%;">Run</button>
      <div id="gt-progress" style="display:none;"><div class="prog-track"><div id="gt-bar" style="height:100%;width:0%;background:var(--accent);border-radius:999px;"></div></div><div id="gt-label" style="font-size:11.5px;color:var(--muted);margin-top:6px;text-align:center;">Working…</div></div>
      <div id="gt-res"><div class="big-num" id="gt-res-num">0 KB</div><div class="lbl" id="gt-res-lbl">Output size</div><div class="modal-actions" style="justify-content:stretch;"><a id="gt-dl" class="btn-primary" style="text-decoration:none;flex:1;">⬇ Save Output</a></div></div>
    </div>
    <div class="modal-actions"><button type="button" class="btn-cancel" id="gt-close">Close</button></div>
  </div>
</div>

<div id="about-modal" class="modal-overlay">
  <div class="modal-box">
    <div class="sheet-handle"></div>
    <h2>About PexiPDF</h2>
    <div class="about-hero">
      <div class="app-brand-mark" style="width:48px;height:48px;border-radius:14px;"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="width:24px;height:24px;"><path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/><path d="M9.5 13h5M9.5 16.5h3.5"/></svg></div>
      <div><div style="font-size:16px;font-weight:700;">PexiPDF by Xcluice</div><div style="font-size:12px;color:var(--muted);margin-top:2px;">Offline PDF Scanner, Converter &amp; Media Studio</div><span class="about-badge" id="about-version-pill">Web App</span></div>
    </div>
    <div style="font-size:12.5px;color:var(--muted);line-height:1.55;">Every document, photo, and note stays on your device. Built with Xcluice's monochrome design system for fast, private mobile productivity.</div>
    <div class="modal-actions"><button type="button" class="btn-cancel" id="about-update-btn">Check Updates</button><button type="button" class="btn-primary" id="about-close-btn">Done</button></div>
  </div>
</div>

<div id="lightbox">
  <button type="button" id="lightbox-close">✕</button>
  <img id="lightbox-img" src="" alt="Preview">
  <div id="lightbox-nav"><button type="button" class="lb-nav-btn" id="lb-prev">‹</button><span id="lightbox-label">1 / 1</span><button type="button" class="lb-nav-btn" id="lb-next">›</button></div>
</div>

<div id="toast"></div>
<canvas id="hidden-canvas" style="display:none;"></canvas>

<script>
"""

final_html = NEW_HEAD_AND_BODY + orig_js + "\n" + ANDROID_BRIDGE_JS + "\n</script>\n</body>\n</html>\n"

# Verify all DOM IDs used by JS exist in HTML
orig_ids = set(re.findall(r"(?:getElementById|\$)\(['\"]([^'\"]+)['\"]\)", orig_js))
html_part = final_html.split("<script>\n// ─── GLOBAL CONTROL")[0]
present_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_part))
missing = sorted(orig_ids - present_ids)
assert not missing, f"Missing DOM IDs: {missing}"

SRC.write_text(final_html, encoding="utf-8")
ASSETS_OUT.parent.mkdir(parents=True, exist_ok=True)
ASSETS_OUT.write_text(final_html, encoding="utf-8")
print(f"Restyled index.html ({len(final_html)} bytes) and verified all {len(orig_ids)} DOM IDs.")
