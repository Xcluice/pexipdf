package com.xcluice.pexipdf

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.ContentUris
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Color as AndroidColor
import android.graphics.Matrix
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
import android.provider.OpenableColumns
import android.provider.Settings
import android.util.Base64
import android.view.ViewGroup
import android.webkit.*
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.OnBackPressedCallback
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.systemBarsPadding
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import androidx.lifecycle.lifecycleScope
import androidx.webkit.WebViewAssetLoader
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.ByteArrayOutputStream
import java.io.File
import java.io.FileOutputStream
import java.util.concurrent.ConcurrentHashMap

class MainActivity : ComponentActivity() {

    private var webView: WebView? = null
    private var webReady = false
    private var refreshPdfsOnResume = false
    private var pendingExternalPdfUri: Uri? = null
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private var pendingCameraPermissionRequest: PermissionRequest? = null
    private var pendingNativeCameraLaunch = false
    private var pendingCameraFile: File? = null
    private var pendingLegacySave: Triple<File, String, String>? = null

    private data class ActiveTransfer(
        val tempFile: File,
        val stream: FileOutputStream,
        val fileName: String,
        val mimeType: String,
        val mode: String
    )
    private val transfers = ConcurrentHashMap<String, ActiveTransfer>()

    private val filePickerLauncher = registerForActivityResult(
        ActivityResultContracts.StartActivityForResult()
    ) { result ->
        val cb = filePathCallback ?: return@registerForActivityResult
        filePathCallback = null
        if (result.resultCode != Activity.RESULT_OK || result.data == null) {
            cb.onReceiveValue(null)
            return@registerForActivityResult
        }
        val data = result.data!!
        val uris = mutableListOf<Uri>()
        data.clipData?.let { clip ->
            for (i in 0 until clip.itemCount) {
                clip.getItemAt(i).uri?.let { uris.add(it) }
            }
        }
        if (uris.isEmpty()) {
            data.data?.let { uris.add(it) }
        }
        cb.onReceiveValue(if (uris.isEmpty()) null else uris.toTypedArray())
    }

    private val cameraPermLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        val req = pendingCameraPermissionRequest
        pendingCameraPermissionRequest = null
        if (req != null) {
            runOnUiThread {
                if (granted) {
                    req.grant(arrayOf(PermissionRequest.RESOURCE_VIDEO_CAPTURE))
                } else {
                    req.deny()
                }
            }
        }
        if (pendingNativeCameraLaunch) {
            pendingNativeCameraLaunch = false
            if (granted) launchSystemCamera()
            else Toast.makeText(this, "Camera permission required", Toast.LENGTH_SHORT).show()
        }
    }

    private val readPermLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { _ ->
        queryAndPushDevicePdfs()
    }

    private val storagePermLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        val pending = pendingLegacySave ?: return@registerForActivityResult
        pendingLegacySave = null
        if (granted) {
            lifecycleScope.launch(Dispatchers.IO) {
                saveTempFileToDownloads(pending.first, pending.second, pending.third)
            }
        } else {
            pending.first.delete()
            Toast.makeText(this, "Storage permission needed to save to Downloads", Toast.LENGTH_LONG).show()
        }
    }

    private val takePictureLauncher = registerForActivityResult(
        ActivityResultContracts.TakePicture()
    ) { success ->
        val photoFile = pendingCameraFile
        pendingCameraFile = null
        if (!success || photoFile == null || !photoFile.exists()) {
            photoFile?.delete()
            return@registerForActivityResult
        }
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val opts = BitmapFactory.Options().apply { inJustDecodeBounds = true }
                BitmapFactory.decodeFile(photoFile.absolutePath, opts)
                val maxDim = 1800
                var sample = 1
                while (opts.outWidth / sample > maxDim * 2 || opts.outHeight / sample > maxDim * 2) {
                    sample *= 2
                }
                val decodeOpts = BitmapFactory.Options().apply { inSampleSize = sample }
                var bmp = BitmapFactory.decodeFile(photoFile.absolutePath, decodeOpts)
                    ?: throw IllegalStateException("Could not decode photo")

                val longest = maxOf(bmp.width, bmp.height)
                if (longest > maxDim) {
                    val scale = maxDim.toFloat() / longest.toFloat()
                    val m = Matrix().apply { postScale(scale, scale) }
                    val scaled = Bitmap.createBitmap(bmp, 0, 0, bmp.width, bmp.height, m, true)
                    if (scaled != bmp) bmp.recycle()
                    bmp = scaled
                }

                val baos = ByteArrayOutputStream()
                bmp.compress(Bitmap.CompressFormat.JPEG, 86, baos)
                bmp.recycle()
                photoFile.delete()

                val bytes = baos.toByteArray()
                val b64 = Base64.encodeToString(bytes, Base64.NO_WRAP)
                val name = "scan_${System.currentTimeMillis()}.jpg"
                withContext(Dispatchers.Main) {
                    webView?.evaluateJavascript(
                        "window.__pexiAddCapturedPhoto && window.__pexiAddCapturedPhoto('$b64', '$name', ${bytes.size})",
                        null
                    )
                }
            } catch (_: Exception) {
                photoFile.delete()
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@MainActivity, "Photo import failed", Toast.LENGTH_SHORT).show()
                }
            }
        }
    }

    private fun launchSystemCamera() {
        try {
            val dir = File(cacheDir, "camera").apply { mkdirs() }
            val f = File(dir, "cap_${System.currentTimeMillis()}.jpg")
            pendingCameraFile = f
            val uri = FileProvider.getUriForFile(this, "${packageName}.files", f)
            takePictureLauncher.launch(uri)
        } catch (_: Exception) {
            Toast.makeText(this, "Could not open camera", Toast.LENGTH_SHORT).show()
        }
    }

    private fun hasFullPdfListAccess(): Boolean {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            Environment.isExternalStorageManager()
        } else {
            ContextCompat.checkSelfPermission(this, Manifest.permission.READ_EXTERNAL_STORAGE) ==
                PackageManager.PERMISSION_GRANTED
        }
    }

    private fun queryAndPushDevicePdfs() {
        lifecycleScope.launch(Dispatchers.IO) {
            val seen = HashSet<String>()
            val list = mutableListOf<JSONObject>()

            // 1. MediaStore.Files query for PDFs
            runCatching {
                val collection = MediaStore.Files.getContentUri("external")
                val cols = mutableListOf(
                    MediaStore.Files.FileColumns._ID,
                    MediaStore.Files.FileColumns.DISPLAY_NAME,
                    MediaStore.Files.FileColumns.SIZE,
                    MediaStore.Files.FileColumns.DATE_MODIFIED
                )
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                    cols.add(MediaStore.Files.FileColumns.RELATIVE_PATH)
                }
                val sel = "${MediaStore.Files.FileColumns.MIME_TYPE} = ? OR ${MediaStore.Files.FileColumns.DISPLAY_NAME} LIKE ?"
                val args = arrayOf("application/pdf", "%.pdf")
                val sort = "${MediaStore.Files.FileColumns.DATE_MODIFIED} DESC"
                contentResolver.query(collection, cols.toTypedArray(), sel, args, sort)?.use { c ->
                    val idCol = c.getColumnIndexOrThrow(MediaStore.Files.FileColumns._ID)
                    val nameCol = c.getColumnIndex(MediaStore.Files.FileColumns.DISPLAY_NAME)
                    val sizeCol = c.getColumnIndex(MediaStore.Files.FileColumns.SIZE)
                    val modCol = c.getColumnIndex(MediaStore.Files.FileColumns.DATE_MODIFIED)
                    val relCol = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                        c.getColumnIndex(MediaStore.Files.FileColumns.RELATIVE_PATH)
                    } else -1

                    while (c.moveToNext() && list.size < 150) {
                        val id = c.getLong(idCol)
                        val name = if (nameCol >= 0) c.getString(nameCol) else null
                        if (name.isNullOrBlank()) continue
                        val size = if (sizeCol >= 0) c.getLong(sizeCol) else 0L
                        val mod = if (modCol >= 0) c.getLong(modCol) else 0L
                        val rel = if (relCol >= 0) (c.getString(relCol) ?: "") else ""
                        val folder = rel.trim('/').substringAfterLast('/', "").ifBlank { "Device" }
                        val key = "${name.lowercase()}_$size"
                        if (!seen.add(key)) continue
                        val uri = ContentUris.withAppendedId(collection, id).toString()
                        list.add(
                            JSONObject()
                                .put("uri", uri)
                                .put("name", name)
                                .put("size", size)
                                .put("modified", mod)
                                .put("folder", folder)
                        )
                    }
                }
            }

            // 2. Direct scan of common folders if full storage access is granted
            if (hasFullPdfListAccess()) {
                val ext = Environment.getExternalStorageDirectory()
                val dirs = listOf(
                    File(ext, "Download"),
                    File(ext, "Download/PexiPDF"),
                    File(ext, "Documents"),
                    File(ext, "WhatsApp/Media/WhatsApp Documents"),
                    File(ext, "Android/media/com.whatsapp/WhatsApp/Media/WhatsApp Documents"),
                    File(ext, "Telegram/Telegram Documents")
                )
                for (d in dirs) {
                    if (!d.exists() || !d.isDirectory) continue
                    d.listFiles()?.forEach { f ->
                        if (f.isFile && f.name.endsWith(".pdf", ignoreCase = true) && list.size < 200) {
                            val key = "${f.name.lowercase()}_${f.length()}"
                            if (seen.add(key)) {
                                list.add(
                                    JSONObject()
                                        .put("uri", Uri.fromFile(f).toString())
                                        .put("name", f.name)
                                        .put("size", f.length())
                                        .put("modified", f.lastModified() / 1000L)
                                        .put("folder", d.name)
                                )
                            }
                        }
                    }
                }
            }

            list.sortByDescending { it.optLong("modified", 0L) }
            val arr = JSONArray()
            list.take(150).forEach { arr.put(it) }
            val payload = JSONObject()
                .put("needsPermission", !hasFullPdfListAccess())
                .put("items", arr)
                .toString()
            val quoted = JSONObject.quote(payload)
            withContext(Dispatchers.Main) {
                webView?.evaluateJavascript(
                    "window.__pexiOnDevicePdfs && window.__pexiOnDevicePdfs($quoted)",
                    null
                )
            }
        }
    }

    private fun extractPdfUri(intent: Intent?): Uri? {
        if (intent == null) return null
        return when (intent.action) {
            Intent.ACTION_VIEW -> intent.data
            Intent.ACTION_SEND -> {
                @Suppress("DEPRECATION")
                intent.getParcelableExtra(Intent.EXTRA_STREAM)
            }
            else -> null
        }
    }

    private fun queryDisplayName(uri: Uri): String {
        if (uri.scheme == "file") {
            return File(uri.path ?: "").name.ifBlank { "document.pdf" }
        }
        var name: String? = null
        runCatching {
            contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) {
                    val idx = c.getColumnIndex(OpenableColumns.DISPLAY_NAME)
                    if (idx >= 0) name = c.getString(idx)
                }
            }
        }
        return name?.takeIf { it.isNotBlank() } ?: uri.lastPathSegment?.substringAfterLast('/') ?: "document.pdf"
    }

    private fun streamExternalPdfToViewer(uri: Uri) {
        lifecycleScope.launch(Dispatchers.IO) {
            try {
                val name = queryDisplayName(uri)
                val quotedName = JSONObject.quote(name)
                withContext(Dispatchers.Main) {
                    webView?.evaluateJavascript(
                        "window.__pexiExternalPdfStart && window.__pexiExternalPdfStart($quotedName)",
                        null
                    )
                }
                val inputStream = if (uri.scheme == "file") {
                    File(uri.path ?: "").inputStream()
                } else {
                    contentResolver.openInputStream(uri)
                } ?: throw IllegalStateException("Cannot read PDF")

                inputStream.use { input ->
                    val buf = ByteArray(256 * 1024)
                    while (true) {
                        val n = input.read(buf)
                        if (n <= 0) break
                        val b64 = Base64.encodeToString(buf, 0, n, Base64.NO_WRAP)
                        withContext(Dispatchers.Main) {
                            webView?.evaluateJavascript(
                                "window.__pexiExternalPdfChunk && window.__pexiExternalPdfChunk('$b64')",
                                null
                            )
                        }
                    }
                }
                withContext(Dispatchers.Main) {
                    webView?.evaluateJavascript(
                        "window.__pexiExternalPdfEnd && window.__pexiExternalPdfEnd()",
                        null
                    )
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    Toast.makeText(this@MainActivity, "Could not open PDF: ${e.message}", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val uri = extractPdfUri(intent)
        if (uri != null) {
            if (webReady) streamExternalPdfToViewer(uri)
            else pendingExternalPdfUri = uri
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        applySystemBars(isDark = true)
        pendingExternalPdfUri = extractPdfUri(intent)

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                val wv = webView
                if (wv == null) {
                    finish()
                    return
                }
                wv.evaluateJavascript("window.__pexiBack ? window.__pexiBack() : false") { res ->
                    if (res != "true") {
                        isEnabled = false
                        onBackPressedDispatcher.onBackPressed()
                        isEnabled = true
                    }
                }
            }
        })

        lifecycleScope.launch { Updater.check() }

        setContent {
            val updateState by Updater.state.collectAsState()
            var darkTheme by remember { mutableStateOf(true) }

            when (val u = updateState) {
                is UpdateState.Required -> ForceUpdateScreen(u)
                else -> {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .background(if (darkTheme) Color(0xFF0A0A0C) else Color(0xFFF4F4F5))
                            .systemBarsPadding()
                    ) {
                        AndroidView(
                            modifier = Modifier.fillMaxSize(),
                            factory = { ctx ->
                                createPexiWebView(ctx) { isDark ->
                                    darkTheme = isDark
                                    applySystemBars(isDark)
                                    webView?.setBackgroundColor(
                                        AndroidColor.parseColor(if (isDark) "#0A0A0C" else "#F4F4F5")
                                    )
                                }
                            }
                        )
                    }
                }
            }
        }
    }

    private fun applySystemBars(isDark: Boolean) {
        val style = if (isDark) {
            SystemBarStyle.dark(AndroidColor.TRANSPARENT)
        } else {
            SystemBarStyle.light(AndroidColor.TRANSPARENT, AndroidColor.TRANSPARENT)
        }
        enableEdgeToEdge(statusBarStyle = style, navigationBarStyle = style)
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun createPexiWebView(
        ctx: android.content.Context,
        onThemeChange: (Boolean) -> Unit
    ): WebView {
        val assetLoader = WebViewAssetLoader.Builder()
            .addPathHandler("/", WebViewAssetLoader.AssetsPathHandler(ctx))
            .build()

        return WebView(ctx).apply {
            layoutParams = ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
            )
            setBackgroundColor(AndroidColor.parseColor("#0A0A0C"))
            overScrollMode = WebView.OVER_SCROLL_NEVER

            settings.apply {
                javaScriptEnabled = true
                domStorageEnabled = true
                databaseEnabled = true
                allowFileAccess = true
                allowContentAccess = true
                mediaPlaybackRequiresUserGesture = false
                mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW
                useWideViewPort = true
                loadWithOverviewMode = true
                setSupportZoom(false)
                builtInZoomControls = false
                displayZoomControls = false
            }

            addJavascriptInterface(PexiBridge(onThemeChange), "PexiBridge")

            webViewClient = object : WebViewClient() {
                override fun shouldInterceptRequest(
                    view: WebView,
                    request: WebResourceRequest
                ): WebResourceResponse? {
                    return assetLoader.shouldInterceptRequest(request.url)
                }

                override fun shouldOverrideUrlLoading(
                    view: WebView,
                    request: WebResourceRequest
                ): Boolean {
                    val uri = request.url
                    if (uri.host == "appassets.androidplatform.net") return false
                    return try {
                        startActivity(Intent(Intent.ACTION_VIEW, uri))
                        true
                    } catch (_: Exception) {
                        false
                    }
                }
            }

            webChromeClient = object : WebChromeClient() {
                override fun onShowFileChooser(
                    webView: WebView,
                    callback: ValueCallback<Array<Uri>>,
                    params: FileChooserParams
                ): Boolean {
                    filePathCallback?.onReceiveValue(null)
                    filePathCallback = callback
                    val mimes = params.acceptTypes
                        .flatMap { it.split(",") }
                        .map { it.trim() }
                        .filter { it.contains("/") }
                        .distinct()
                    val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        type = if (mimes.size == 1) mimes[0] else "*/*"
                        if (mimes.size > 1) {
                            putExtra(Intent.EXTRA_MIME_TYPES, mimes.toTypedArray())
                        }
                        if (params.mode == FileChooserParams.MODE_OPEN_MULTIPLE) {
                            putExtra(Intent.EXTRA_ALLOW_MULTIPLE, true)
                        }
                    }
                    return try {
                        filePickerLauncher.launch(Intent.createChooser(intent, "Select file"))
                        true
                    } catch (_: Exception) {
                        filePathCallback = null
                        false
                    }
                }

                override fun onPermissionRequest(request: PermissionRequest) {
                    val needsCam = request.resources.contains(PermissionRequest.RESOURCE_VIDEO_CAPTURE)
                    if (!needsCam) {
                        runOnUiThread { request.deny() }
                        return
                    }
                    if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.CAMERA)
                        == PackageManager.PERMISSION_GRANTED
                    ) {
                        runOnUiThread {
                            request.grant(arrayOf(PermissionRequest.RESOURCE_VIDEO_CAPTURE))
                        }
                    } else {
                        pendingCameraPermissionRequest = request
                        runOnUiThread {
                            cameraPermLauncher.launch(Manifest.permission.CAMERA)
                        }
                    }
                }
            }

            webView = this
            loadUrl("https://appassets.androidplatform.net/index.html")
        }
    }

    override fun onPause() {
        webView?.onPause()
        super.onPause()
    }

    override fun onResume() {
        super.onResume()
        webView?.onResume()
        if (refreshPdfsOnResume) {
            refreshPdfsOnResume = false
            queryAndPushDevicePdfs()
        }
    }

    override fun onDestroy() {
        transfers.values.forEach {
            runCatching { it.stream.close() }
            runCatching { it.tempFile.delete() }
        }
        transfers.clear()
        webView?.destroy()
        webView = null
        super.onDestroy()
    }

    private suspend fun saveTempFileToDownloads(tempFile: File, safeName: String, mime: String) {
        try {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                val values = ContentValues().apply {
                    put(MediaStore.Downloads.DISPLAY_NAME, safeName)
                    put(MediaStore.Downloads.MIME_TYPE, mime)
                    put(MediaStore.Downloads.RELATIVE_PATH, "${Environment.DIRECTORY_DOWNLOADS}/PexiPDF")
                    put(MediaStore.Downloads.IS_PENDING, 1)
                }
                val resolver = contentResolver
                val uri = resolver.insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, values)
                    ?: throw IllegalStateException("Cannot create download entry")
                resolver.openOutputStream(uri)?.use { out ->
                    tempFile.inputStream().use { it.copyTo(out) }
                }
                values.clear()
                values.put(MediaStore.Downloads.IS_PENDING, 0)
                resolver.update(uri, values, null, null)
                tempFile.delete()
            } else {
                if (ContextCompat.checkSelfPermission(this, Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED
                ) {
                    pendingLegacySave = Triple(tempFile, safeName, mime)
                    withContext(Dispatchers.Main) {
                        storagePermLauncher.launch(Manifest.permission.WRITE_EXTERNAL_STORAGE)
                    }
                    return
                }
                @Suppress("DEPRECATION")
                val dir = File(
                    Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                    "PexiPDF"
                ).apply { mkdirs() }
                val dest = File(dir, safeName)
                tempFile.inputStream().use { src -> dest.outputStream().use { src.copyTo(it) } }
                tempFile.delete()
            }
            withContext(Dispatchers.Main) {
                Toast.makeText(
                    this@MainActivity,
                    "Saved to Downloads/PexiPDF/$safeName",
                    Toast.LENGTH_LONG
                ).show()
            }
        } catch (e: Exception) {
            tempFile.delete()
            withContext(Dispatchers.Main) {
                Toast.makeText(
                    this@MainActivity,
                    "Save failed: ${e.message}",
                    Toast.LENGTH_LONG
                ).show()
            }
        }
    }

    private suspend fun shareTempFile(tempFile: File, safeName: String, mime: String) {
        try {
            val dir = File(cacheDir, "shared").apply { mkdirs() }
            val dest = File(dir, safeName)
            tempFile.inputStream().use { src -> dest.outputStream().use { src.copyTo(it) } }
            tempFile.delete()
            val uri = FileProvider.getUriForFile(this@MainActivity, "${packageName}.files", dest)
            val intent = Intent(Intent.ACTION_SEND).apply {
                type = mime
                putExtra(Intent.EXTRA_STREAM, uri)
                addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            }
            withContext(Dispatchers.Main) {
                startActivity(Intent.createChooser(intent, "Share $safeName"))
            }
        } catch (e: Exception) {
            tempFile.delete()
            withContext(Dispatchers.Main) {
                Toast.makeText(
                    this@MainActivity,
                    "Share failed: ${e.message}",
                    Toast.LENGTH_SHORT
                ).show()
            }
        }
    }

    inner class PexiBridge(private val onThemeChange: (Boolean) -> Unit) {
        @JavascriptInterface
        fun onReady() {
            runOnUiThread {
                webReady = true
                val pending = pendingExternalPdfUri
                pendingExternalPdfUri = null
                if (pending != null) {
                    streamExternalPdfToViewer(pending)
                }
            }
        }

        @JavascriptInterface
        fun listDevicePdfs() {
            queryAndPushDevicePdfs()
        }

        @JavascriptInterface
        fun requestPdfListPermission() {
            runOnUiThread {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                    refreshPdfsOnResume = true
                    try {
                        startActivity(
                            Intent(
                                Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                                Uri.parse("package:$packageName")
                            )
                        )
                    } catch (_: Exception) {
                        startActivity(Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION))
                    }
                } else {
                    readPermLauncher.launch(Manifest.permission.READ_EXTERNAL_STORAGE)
                }
            }
        }

        @JavascriptInterface
        fun openPdfUri(uriString: String) {
            if (uriString.isBlank()) return
            streamExternalPdfToViewer(Uri.parse(uriString))
        }

        @JavascriptInterface
        fun getAppVersion(): String = BuildConfig.VERSION_NAME

        @JavascriptInterface
        fun setTheme(isDark: Boolean) {
            runOnUiThread { onThemeChange(isDark) }
        }

        @JavascriptInterface
        fun openNativeCamera() {
            runOnUiThread {
                if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.CAMERA)
                    == PackageManager.PERMISSION_GRANTED
                ) {
                    launchSystemCamera()
                } else {
                    pendingNativeCameraLaunch = true
                    cameraPermLauncher.launch(Manifest.permission.CAMERA)
                }
            }
        }

        @JavascriptInterface
        fun checkForUpdates() {
            lifecycleScope.launch {
                val res = Updater.check()
                if (res !is UpdateState.Required) {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(
                            this@MainActivity,
                            "PexiPDF v${BuildConfig.VERSION_NAME} is up to date",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            }
        }

        @JavascriptInterface
        fun beginTransfer(id: String, rawName: String, mimeType: String, mode: String) {
            val safeName = rawName.replace(Regex("[^a-zA-Z0-9._-]"), "_").ifBlank { "pexipdf_output.pdf" }
            val mime = mimeType.ifBlank { "application/octet-stream" }
            val dir = File(cacheDir, "xfer").apply { mkdirs() }
            val temp = File(dir, "${id}_$safeName")
            transfers[id] = ActiveTransfer(temp, FileOutputStream(temp), safeName, mime, mode)
        }

        @JavascriptInterface
        fun appendTransfer(id: String, base64Chunk: String) {
            val xfer = transfers[id] ?: return
            val bytes = Base64.decode(base64Chunk, Base64.DEFAULT)
            xfer.stream.write(bytes)
        }

        @JavascriptInterface
        fun finishTransfer(id: String) {
            val xfer = transfers.remove(id) ?: return
            lifecycleScope.launch(Dispatchers.IO) {
                runCatching { xfer.stream.flush(); xfer.stream.close() }
                if (xfer.mode == "share") {
                    shareTempFile(xfer.tempFile, xfer.fileName, xfer.mimeType)
                } else {
                    saveTempFileToDownloads(xfer.tempFile, xfer.fileName, xfer.mimeType)
                }
            }
        }

        @JavascriptInterface
        fun saveFile(base64: String, rawName: String, mimeType: String) {
            val safeName = rawName.replace(Regex("[^a-zA-Z0-9._-]"), "_").ifBlank { "pexipdf_output.pdf" }
            val mime = mimeType.ifBlank { "application/octet-stream" }
            lifecycleScope.launch(Dispatchers.IO) {
                val dir = File(cacheDir, "xfer").apply { mkdirs() }
                val temp = File(dir, "direct_${System.currentTimeMillis()}_$safeName")
                temp.writeBytes(Base64.decode(base64, Base64.DEFAULT))
                saveTempFileToDownloads(temp, safeName, mime)
            }
        }

        @JavascriptInterface
        fun shareFile(base64: String, rawName: String, mimeType: String) {
            val safeName = rawName.replace(Regex("[^a-zA-Z0-9._-]"), "_").ifBlank { "pexipdf_output.pdf" }
            val mime = mimeType.ifBlank { "application/pdf" }
            lifecycleScope.launch(Dispatchers.IO) {
                val dir = File(cacheDir, "xfer").apply { mkdirs() }
                val temp = File(dir, "share_${System.currentTimeMillis()}_$safeName")
                temp.writeBytes(Base64.decode(base64, Base64.DEFAULT))
                shareTempFile(temp, safeName, mime)
            }
        }
    }
}
