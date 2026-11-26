package com.xcluice.pexipdf

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.launch
import java.io.File

@Composable
fun ForceUpdateScreen(update: UpdateState.Required) {
    val ctx = LocalContext.current
    val scope = rememberCoroutineScope()
    var downloading by remember { mutableStateOf(false) }
    var progress by remember { mutableFloatStateOf(0f) }
    var downloadedApk by remember { mutableStateOf<File?>(null) }
    var errorMsg by remember { mutableStateOf<String?>(null) }
    var needsPermission by remember { mutableStateOf(false) }

    val animProgress by animateFloatAsState(targetValue = progress, label = "upd_prog")

    val bg = Color(0xFF0A0A0C)
    val surface = Color(0xFF141417)
    val border = Color(0xFF26262C)
    val ink = Color(0xFFF4F4F6)
    val muted = Color(0xFF8E8E98)
    val accent = Color(0xFF8EA2FF)

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(bg)
            .systemBarsPadding()
            .padding(22.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.Center
        ) {
            Surface(
                shape = RoundedCornerShape(999.dp),
                color = accent.copy(alpha = 0.14f)
            ) {
                Text(
                    text = "UPDATE REQUIRED · v${BuildConfig.VERSION_NAME} → v${update.version}",
                    color = accent,
                    fontSize = 11.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 0.5.sp,
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                )
            }

            Spacer(Modifier.height(16.dp))

            Text(
                text = "New PexiPDF update ready",
                color = ink,
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                lineHeight = 32.sp
            )

            Spacer(Modifier.height(8.dp))

            Text(
                text = "Install the latest release from Xcluice to keep using PexiPDF with the newest tools and fixes.",
                color = muted,
                fontSize = 14.sp,
                lineHeight = 20.sp
            )

            Spacer(Modifier.height(22.dp))

            Surface(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(22.dp),
                color = surface,
                border = BorderStroke(1.dp, border)
            ) {
                Column(modifier = Modifier.padding(18.dp)) {
                    Text(
                        text = "What's new",
                        color = ink,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(Modifier.height(10.dp))
                    Text(
                        text = update.notes,
                        color = muted,
                        fontSize = 13.sp,
                        lineHeight = 20.sp
                    )
                }
            }

            Spacer(Modifier.height(24.dp))

            if (downloading) {
                Column(modifier = Modifier.fillMaxWidth()) {
                    LinearProgressIndicator(
                        progress = { animProgress },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(8.dp)
                            .clip(RoundedCornerShape(999.dp)),
                        color = accent,
                        trackColor = border
                    )
                    Spacer(Modifier.height(8.dp))
                    Text(
                        text = "Downloading update… ${(progress * 100).toInt()}%",
                        color = muted,
                        fontSize = 12.sp
                    )
                }
            } else {
                Button(
                    onClick = {
                        errorMsg = null
                        val existing = downloadedApk
                        if (existing != null && existing.exists()) {
                            needsPermission = !Updater.install(ctx, existing)
                            return@Button
                        }
                        scope.launch {
                            downloading = true
                            progress = 0.04f
                            try {
                                val file = Updater.download(ctx, update.apkUrl) { p ->
                                    progress = p
                                }
                                downloadedApk = file
                                downloading = false
                                needsPermission = !Updater.install(ctx, file)
                            } catch (e: Exception) {
                                downloading = false
                                errorMsg = e.message ?: "Download failed. Please retry."
                            }
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(54.dp),
                    shape = RoundedCornerShape(999.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = ink,
                        contentColor = bg
                    )
                ) {
                    Text(
                        text = if (downloadedApk != null) "Install v${update.version}" else "Download & Update",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold
                    )
                }
            }

            if (needsPermission) {
                Spacer(Modifier.height(12.dp))
                Text(
                    text = "Allow \"Install unknown apps\" for PexiPDF in Settings, then tap Install again.",
                    color = accent,
                    fontSize = 12.sp,
                    lineHeight = 17.sp
                )
            }

            if (errorMsg != null) {
                Spacer(Modifier.height(12.dp))
                Text(
                    text = errorMsg ?: "",
                    color = Color(0xFFE8696A),
                    fontSize = 12.sp
                )
            }
        }
    }
}
