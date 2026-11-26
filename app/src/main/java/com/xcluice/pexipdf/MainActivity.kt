package com.xcluice.pexipdf

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.ContentValues
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Color as AndroidColor
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.Environment
import android.provider.MediaStore
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
import java.io.File

class MainActivity : ComponentActivity() {

    private var webView: WebView? = null
    private var filePathCallback: ValueCallback<Array<Uri>>? = null
    private var pendingCameraPermissionRequest: PermissionRequest? = null

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
            if (granted) req.grant(req.resources) else req.deny()
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        applySystemBars(isDark = true)

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
                    val intent = Intent(Intent.ACTION_GET_CONTENT).apply {
                        addCategory(Intent.CATEGORY_OPENABLE)
                        val accepts = params.acceptTypes.filter { it.isNotBlank() }
                        type = if (accepts.size == 1 && accepts[0].contains("/")) accepts[0] else "*/*"
                        if (accepts.size > 1) {
                            val mimes = accepts.filter { it.contains("/") }.toTypedArray()
                            if (mimes.isNotEmpty()) putExtra(Intent.EXTRA_MIME_TYPES, mimes)
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
                        request.deny()
                        return
                    }
                    if (ContextCompat.checkSelfPermission(this@MainActivity, Manifest.permission.CAMERA)
                        == PackageManager.PERMISSION_GRANTED
                    ) {
                        request.grant(request.resources)
                    } else {
                        pendingCameraPermissionRequest = request
                        cameraPermLauncher.launch(Manifest.permission.CAMERA)
                    }
                }
            }

            webView = this
            loadUrl("https://appassets.androidplatform.net/index.html")
        }
    }

    override fun onDestroy() {
        webView?.destroy()
        webView = null
        super.onDestroy()
    }

    inner class PexiBridge(private val onThemeChange: (Boolean) -> Unit) {
        @JavascriptInterface
        fun getAppVersion(): String = BuildConfig.VERSION_NAME

        @JavascriptInterface
        fun setTheme(isDark: Boolean) {
            runOnUiThread { onThemeChange(isDark) }
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
        fun saveFile(base64: String, rawName: String, mimeType: String) {
            val safeName = rawName.replace(Regex("[^a-zA-Z0-9._-]"), "_").ifBlank { "pexipdf_output.pdf" }
            val mime = mimeType.ifBlank { "application/octet-stream" }
            lifecycleScope.launch(Dispatchers.IO) {
                try {
                    val bytes = Base64.decode(base64, Base64.DEFAULT)
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
                        resolver.openOutputStream(uri)?.use { it.write(bytes) }
                        values.clear()
                        values.put(MediaStore.Downloads.IS_PENDING, 0)
                        resolver.update(uri, values, null, null)
                    } else {
                        @Suppress("DEPRECATION")
                        val dir = File(
                            Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS),
                            "PexiPDF"
                        ).apply { mkdirs() }
                        File(dir, safeName).writeBytes(bytes)
                    }
                    withContext(Dispatchers.Main) {
                        Toast.makeText(
                            this@MainActivity,
                            "Saved to Downloads/PexiPDF/$safeName",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(
                            this@MainActivity,
                            "Save failed: ${e.message}",
                            Toast.LENGTH_LONG
                        ).show()
                    }
                }
            }
        }

        @JavascriptInterface
        fun shareFile(base64: String, rawName: String, mimeType: String) {
            val safeName = rawName.replace(Regex("[^a-zA-Z0-9._-]"), "_").ifBlank { "pexipdf_output.pdf" }
            val mime = mimeType.ifBlank { "application/pdf" }
            lifecycleScope.launch(Dispatchers.IO) {
                try {
                    val bytes = Base64.decode(base64, Base64.DEFAULT)
                    val dir = File(cacheDir, "shared").apply { mkdirs() }
                    val f = File(dir, safeName)
                    f.writeBytes(bytes)
                    val uri = FileProvider.getUriForFile(this@MainActivity, "${packageName}.files", f)
                    val intent = Intent(Intent.ACTION_SEND).apply {
                        type = mime
                        putExtra(Intent.EXTRA_STREAM, uri)
                        addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                    }
                    withContext(Dispatchers.Main) {
                        startActivity(Intent.createChooser(intent, "Share $safeName"))
                    }
                } catch (e: Exception) {
                    withContext(Dispatchers.Main) {
                        Toast.makeText(
                            this@MainActivity,
                            "Share failed: ${e.message}",
                            Toast.LENGTH_SHORT
                        ).show()
                    }
                }
            }
        }
    }
}
