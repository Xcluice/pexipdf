package com.xcluice.pexipdf

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.core.content.FileProvider
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.util.concurrent.TimeUnit

sealed interface UpdateState {
    data object Unknown : UpdateState
    data object Current : UpdateState
    data class Required(val version: String, val apkUrl: String, val notes: String) : UpdateState
}

object Updater {
    private const val API = "https://api.github.com/repos/Xcluice/pexipdf/releases/latest"
    private val client = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS)
        .followRedirects(true)
        .build()

    val state = MutableStateFlow<UpdateState>(UpdateState.Unknown)

    private fun newer(remote: String, local: String): Boolean {
        val a = remote.removePrefix("v").split('.').map { it.toIntOrNull() ?: 0 }
        val b = local.removePrefix("v").split('.').map { it.toIntOrNull() ?: 0 }
        for (i in 0 until maxOf(a.size, b.size)) {
            val x = a.getOrElse(i) { 0 }
            val y = b.getOrElse(i) { 0 }
            if (x != y) return x > y
        }
        return false
    }

    private fun cleanNotes(raw: String): String {
        val lines = raw.lines()
            .map { it.trim() }
            .filter { line ->
                line.isNotEmpty() &&
                    !line.startsWith("#") &&
                    !line.startsWith("**Full Changelog**")
            }
            .map { line ->
                line.replace(Regex("^[-*]\\s+"), "• ")
                    .replace(Regex("\\s+by\\s+@\\S+\\s+in\\s+https?://\\S+"), "")
                    .replace(Regex("\\s+in\\s+https?://\\S+"), "")
                    .trim()
            }
            .filter { it.isNotEmpty() }
        return if (lines.isNotEmpty()) lines.joinToString("\n") else "UI improvements, performance updates, and bug fixes."
    }

    suspend fun check(): UpdateState = withContext(Dispatchers.IO) {
        val next = try {
            val req = Request.Builder()
                .url(API)
                .header("Accept", "application/vnd.github+json")
                .header("User-Agent", "PexiPDF-Android/${BuildConfig.VERSION_NAME}")
                .build()
            val body = client.newCall(req).execute().use { r ->
                if (!r.isSuccessful) return@withContext UpdateState.Current.also { state.value = it }
                r.body?.string() ?: ""
            }
            val json = JSONObject(body)
            val tag = json.getString("tag_name")
            val notes = cleanNotes(json.optString("body", ""))
            val assets = json.getJSONArray("assets")
            var apk: String? = null
            for (i in 0 until assets.length()) {
                val a = assets.getJSONObject(i)
                if (a.getString("name").endsWith(".apk", ignoreCase = true)) {
                    apk = a.getString("browser_download_url")
                    break
                }
            }
            if (apk != null && newer(tag, BuildConfig.VERSION_NAME)) {
                UpdateState.Required(tag.removePrefix("v"), apk, notes)
            } else {
                UpdateState.Current
            }
        } catch (_: Exception) {
            UpdateState.Current
        }
        state.value = next
        next
    }

    suspend fun download(ctx: Context, url: String, onProgress: (Float) -> Unit): File =
        withContext(Dispatchers.IO) {
            val dir = File(ctx.cacheDir, "update").apply { deleteRecursively(); mkdirs() }
            val outFile = File(dir, "PexiPDF-update.apk")
            val req = Request.Builder()
                .url(url)
                .header("User-Agent", "PexiPDF-Android/${BuildConfig.VERSION_NAME}")
                .build()
            client.newCall(req).execute().use { r ->
                if (!r.isSuccessful) throw IOException("HTTP ${r.code}")
                val body = r.body ?: throw IOException("Empty response")
                val total = body.contentLength().coerceAtLeast(1L)
                var read = 0L
                body.byteStream().use { src ->
                    outFile.outputStream().use { dst ->
                        val buf = ByteArray(32 * 1024)
                        while (true) {
                            val n = src.read(buf)
                            if (n < 0) break
                            dst.write(buf, 0, n)
                            read += n
                            onProgress((read.toFloat() / total).coerceIn(0f, 1f))
                        }
                    }
                }
            }
            outFile
        }

    fun install(ctx: Context, apkFile: File): Boolean {
        if (Build.VERSION.SDK_INT >= 26 && !ctx.packageManager.canRequestPackageInstalls()) {
            ctx.startActivity(
                Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${ctx.packageName}"))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            )
            return false
        }
        val uri = FileProvider.getUriForFile(ctx, "${ctx.packageName}.files", apkFile)
        ctx.startActivity(
            Intent(Intent.ACTION_VIEW)
                .setDataAndType(uri, "application/vnd.android.package-archive")
                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION or Intent.FLAG_ACTIVITY_NEW_TASK)
        )
        return true
    }
}
