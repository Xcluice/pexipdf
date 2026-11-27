#!/usr/bin/env python3
"""Idempotent Android app-style UI restyler for PexiPDF by Xcluice (Material 3 SVGs + Device PDF List + Pro Reader)."""
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

# 1. Sync theme with Android system bars & settings toggle
if "settings-dark-toggle" not in orig_js:
    orig_js = orig_js.replace(
        "localStorage.setItem('pexipdf_theme', isDark ? 'dark' : 'light');",
        "localStorage.setItem('pexipdf_theme', isDark ? 'dark' : 'light');\n"
        "  const st = document.getElementById('settings-dark-toggle'); if (st) st.checked = !!isDark;\n"
        "  const mc = document.querySelector('meta[name=\"theme-color\"]'); if (mc) mc.setAttribute('content', isDark ? '#0A0A0C' : '#F4F4F5');\n"
        "  if (window.PexiBridge && window.PexiBridge.setTheme) { try { window.PexiBridge.setTheme(!!isDark); } catch(_){} }"
    )

# 2. FFmpeg corePath fallback for Android WebView (keeps APK ~1 MB)
if "https://pexipdf.vercel.app" not in orig_js:
    orig_js = orig_js.replace(
        "corePath: location.origin + '/vendor/ffmpeg-core/ffmpeg-core.js',",
        "corePath: (window.PexiBridge ? 'https://pexipdf.vercel.app' : location.origin) + '/vendor/ffmpeg-core/ffmpeg-core.js',"
    )

# 3. Fix Pages workspace flex layout & sync page count
if "window.__pexiSyncPages" not in orig_js:
    orig_js = orig_js.replace(
        "function renderGrid() {",
        "function renderGrid() {\n  if (window.__pexiSyncPages) window.__pexiSyncPages(images.length);"
    )
    orig_js = orig_js.replace(
        "updateEstSize();",
        "updateEstSize(); if (window.__pexiSyncPages) window.__pexiSyncPages(images.length);"
    )
orig_js = orig_js.replace(
    "if (!images.length) { sec.style.display = 'none'; empty.style.display = 'block';",
    "if (!images.length) { sec.style.display = 'none'; empty.style.display = 'none';"
)
orig_js = orig_js.replace(
    "if (!images.length) { sec.style.display = 'none'; empty.style.display = 'flex';",
    "if (!images.length) { sec.style.display = 'none'; empty.style.display = 'none';"
)
orig_js = orig_js.replace(
    "sec.style.display = 'block'; empty.style.display = 'none';",
    "sec.style.display = 'flex'; empty.style.display = 'none';"
)

# 4. Native Android ShareSheet hook
if "window.__pexiShareBlob" not in orig_js:
    orig_js = orig_js.replace(
        "if (navigator.share) await navigator.share({ files: [new File([lastPdfBlob], fileName, { type: 'application/pdf' })], title: fileName }).catch(() => {});",
        "if (window.PexiBridge && window.PexiBridge.shareFile && lastPdfBlob) { window.__pexiShareBlob(lastPdfBlob, fileName, 'application/pdf'); return; }\n"
        "  if (navigator.share) await navigator.share({ files: [new File([lastPdfBlob], fileName, { type: 'application/pdf' })], title: fileName }).catch(() => {});"
    )

# 5. Fast Camera Scanner replacement
old_cam_pattern = re.compile(
    r"(?:let camFacing =|document\.getElementById\('btn-camera'\)\.addEventListener\('click')[\s\S]*?// ─── TEXT NOTE CONVERT ENGINE",
    re.M
)
fast_cam_js = r"""let camFacing = 'environment';
let camSnapping = false;

async function startCameraStream(facing) {
  if (currentMediaStream) {
    currentMediaStream.getTracks().forEach(t => t.stop());
    currentMediaStream = null;
  }
  const constraintsList = [
    { video: { facingMode: { ideal: facing }, width: { ideal: 1280 }, height: { ideal: 960 } }, audio: false },
    { video: { facingMode: facing }, audio: false },
    { video: true, audio: false }
  ];
  let stream = null;
  let lastErr = null;
  for (const c of constraintsList) {
    try {
      stream = await navigator.mediaDevices.getUserMedia(c);
      break;
    } catch (e) { lastErr = e; }
  }
  if (!stream) throw lastErr || new Error('Camera unavailable');
  currentMediaStream = stream;
  videoStream.srcObject = stream;
  videoStream.muted = true;
  videoStream.playsInline = true;
  await videoStream.play().catch(() => {});
}

document.getElementById('btn-camera').addEventListener('click', async () => {
  try {
    camModal.style.display = 'flex';
    camCounter.textContent = images.length;
    await startCameraStream(camFacing);
  } catch (err) {
    camModal.style.display = 'none';
    if (window.PexiBridge && window.PexiBridge.openNativeCamera) {
      window.PexiBridge.openNativeCamera();
    } else {
      showToast('Camera unavailable — check camera permission');
    }
  }
});

document.getElementById('cam-flip-btn')?.addEventListener('click', async () => {
  camFacing = camFacing === 'environment' ? 'user' : 'environment';
  try { await startCameraStream(camFacing); } catch (_) { showToast('Could not switch camera'); }
});

document.getElementById('cam-native-btn')?.addEventListener('click', () => {
  if (window.PexiBridge && window.PexiBridge.openNativeCamera) {
    if (currentMediaStream) { currentMediaStream.getTracks().forEach(t => t.stop()); currentMediaStream = null; }
    videoStream.srcObject = null;
    camModal.style.display = 'none';
    window.PexiBridge.openNativeCamera();
  }
});

document.getElementById('cam-close-btn').addEventListener('click', () => {
  if (currentMediaStream) {
    currentMediaStream.getTracks().forEach(t => t.stop());
    currentMediaStream = null;
  }
  videoStream.srcObject = null;
  camModal.style.display = 'none';
  renderGrid();
});

document.getElementById('cam-snap-btn').addEventListener('click', () => {
  if (camSnapping || !videoStream.videoWidth || !videoStream.videoHeight) return;
  camSnapping = true;
  const flash = document.getElementById('cam-flash');
  flash.style.opacity = '0.85';
  setTimeout(() => { flash.style.opacity = '0'; }, 75);

  const vw = videoStream.videoWidth, vh = videoStream.videoHeight;
  const maxSide = 1440;
  const scale = Math.min(1, maxSide / Math.max(vw, vh));
  const tw = Math.round(vw * scale), th = Math.round(vh * scale);
  if (hiddenCanvas.width !== tw || hiddenCanvas.height !== th) {
    hiddenCanvas.width = tw;
    hiddenCanvas.height = th;
  }
  hiddenCtx.drawImage(videoStream, 0, 0, tw, th);
  const nextCount = images.length + 1;
  camCounter.textContent = nextCount;
  hiddenCanvas.toBlob(blob => {
    camSnapping = false;
    if (!blob) return;
    images.push({
      file: blob,
      url: URL.createObjectURL(blob),
      name: 'scan_' + Date.now() + '.jpg',
      size: blob.size,
      rotation: 0,
      selected: false
    });
    camCounter.textContent = images.length;
    showToast('Page ' + images.length + ' captured', 1200);
  }, 'image/jpeg', 0.84);
});

// ─── TEXT NOTE CONVERT ENGINE"""

if old_cam_pattern.search(orig_js):
    orig_js = old_cam_pattern.sub(lambda _: fast_cam_js, orig_js, count=1)

_SCRIPT_DIR = Path(__file__).resolve().parent
ANDROID_BRIDGE_JS = (_SCRIPT_DIR / "android_bridge.js").read_text(encoding="utf-8")
NEW_HEAD_AND_BODY = (
    (_SCRIPT_DIR / "ui_head.html").read_text(encoding="utf-8")
    + (_SCRIPT_DIR / "ui_body.html").read_text(encoding="utf-8")
)

final_html = NEW_HEAD_AND_BODY + orig_js + "\n" + ANDROID_BRIDGE_JS + "\n</script>\n</body>\n</html>\n"

orig_ids = set(re.findall(r"(?:getElementById|\$)\(['\"]([^'\"]+)['\"]\)", orig_js))
html_part = final_html.split("<script>\n// ─── GLOBAL CONTROL")[0]
present_ids = set(re.findall(r'id=["\']([^"\']+)["\']', html_part))
missing = sorted(orig_ids - present_ids)
assert not missing, f"Missing DOM IDs: {missing}"

SRC.write_text(final_html, encoding="utf-8")
ASSETS_OUT.parent.mkdir(parents=True, exist_ok=True)
ASSETS_OUT.write_text(final_html, encoding="utf-8")
print(f"Restyled index.html ({len(final_html)} bytes) and verified all {len(orig_ids)} DOM IDs.")
