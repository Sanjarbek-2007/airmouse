package com.aircursor.service

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.SystemClock
import androidx.camera.core.ImageProxy
import com.google.mediapipe.framework.image.BitmapImageBuilder
import com.google.mediapipe.tasks.core.BaseOptions
import com.google.mediapipe.tasks.vision.core.RunningMode
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarker
import com.google.mediapipe.tasks.vision.handlandmarker.HandLandmarkerResult

/**
 * MediaPipe hand landmarks from CameraX frames. Frames are rotated upright (and optionally
 * mirrored) before detection so landmark x/y are directly usable by the gesture engine.
 */
class HandTracker(
    context: Context,
    private val onHand: (pts: FloatArray?, width: Int, height: Int) -> Unit,
    private val onError: (String) -> Unit,
) {
    private val landmarker: HandLandmarker

    init {
        val options = HandLandmarker.HandLandmarkerOptions.builder()
            .setBaseOptions(BaseOptions.builder().setModelAssetPath(MODEL).build())
            .setRunningMode(RunningMode.LIVE_STREAM)
            .setNumHands(1)
            .setMinHandDetectionConfidence(0.6f)
            .setMinHandPresenceConfidence(0.6f)
            .setMinTrackingConfidence(0.5f)
            .setResultListener { result: HandLandmarkerResult, image ->
                val hand = result.landmarks().firstOrNull()
                val pts = hand?.let { lm -> FloatArray(42).also { a -> lm.forEachIndexed { i, p -> if (i < 21) { a[i * 2] = p.x(); a[i * 2 + 1] = p.y() } } } }
                onHand(pts, image.width, image.height)
            }
            .setErrorListener { e -> onError(e.message ?: "hand tracking error") }
            .build()
        landmarker = HandLandmarker.createFromOptions(context, options)
    }

    /** Analyzer entry point (CameraX background thread). Always closes the frame. */
    fun analyze(frame: ImageProxy, mirror: Boolean) {
        val bitmap = Bitmap.createBitmap(frame.width, frame.height, Bitmap.Config.ARGB_8888)
        frame.use { bitmap.copyPixelsFromBuffer(it.planes[0].buffer) }
        val m = Matrix().apply {
            postRotate(frame.imageInfo.rotationDegrees.toFloat())
            if (mirror) postScale(-1f, 1f, frame.width / 2f, frame.height / 2f)
        }
        val upright = Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, m, true)
        bitmap.recycle()
        landmarker.detectAsync(BitmapImageBuilder(upright).build(), SystemClock.uptimeMillis())
    }

    fun close() = runCatching { landmarker.close() }

    companion object { const val MODEL = "hand_landmarker.task" }
}
