package com.aircursor.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.lifecycle.LifecycleService
import com.aircursor.MainActivity
import com.aircursor.R
import com.aircursor.engine.Controller
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Foreground service (type "camera") so hand control keeps working with the screen on and any
 * app in front. Pipeline: CameraX frame -> MediaPipe hand landmarks -> [Controller] -> [PhoneSink].
 */
class AirCursorService : LifecycleService() {
    private val lock = Any()
    private val main = Handler(Looper.getMainLooper())
    private lateinit var sink: PhoneSink
    private lateinit var controller: Controller
    private var tracker: HandTracker? = null
    private var analysisExecutor: ExecutorService? = null
    private var provider: ProcessCameraProvider? = null
    private var boundFacing = ""
    private var lastFrameNs = 0L
    private var lastShownPause = false
    private var fps = 0.0
    private var lastResultNs = 0L

    private val watchdog = object : Runnable {
        override fun run() {
            // Camera stalled (app killed the camera, thermal throttling...): treat as "no hand" so
            // a held touch is released rather than left stuck.
            if (System.nanoTime() - lastFrameNs > 500_000_000L) synchronized(lock) { controller.lost(now()) }
            main.postDelayed(this, 250)
        }
    }

    private fun now() = System.nanoTime() / 1e9

    // ------------------------------------------------------------- lifecycle
    override fun onCreate() {
        super.onCreate()
        SettingsStore.ensureLoaded(this)
        sink = PhoneSink(this)
        val width = resources.displayMetrics.widthPixels.toDouble()
        controller = Controller(SettingsStore.engine, sink, baseScalePx = 0.40 * width, onTrip = { reason ->
            EngineBus.error = reason
            refreshUi()
        })
        createChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        when (intent?.action) {
            ACTION_TOGGLE -> { togglePauseInternal(); return START_NOT_STICKY }
            ACTION_STOP -> { stopSelf(); return START_NOT_STICKY }
        }
        if (tracker != null) return START_NOT_STICKY   // already running (repeated start command)
        instance = this
        startInForeground()
        if (!startEngine()) { stopSelf(); return START_NOT_STICKY }
        return START_NOT_STICKY   // never auto-restart: control must always be a conscious choice
    }

    override fun onDestroy() {
        main.removeCallbacksAndMessages(null)
        runCatching { provider?.unbindAll() }
        synchronized(lock) { controller.shutdown() }
        tracker?.close(); tracker = null
        analysisExecutor?.shutdown()
        instance = null
        AirAccessibilityService.instance?.setRunning(false, false)
        EngineBus.view = com.aircursor.engine.EngineView()
        super.onDestroy()
    }

    // ----------------------------------------------------------------- engine
    private fun startEngine(): Boolean {
        EngineBus.error = ""
        if (AirAccessibilityService.instance == null) { EngineBus.error = "Turn on the AirCursor accessibility service first."; return false }
        try {
            tracker = HandTracker(this, ::onHand) { msg -> EngineBus.error = msg }
        } catch (e: Exception) {
            EngineBus.error = "Could not load hand model: ${e.message}"; return false
        }
        analysisExecutor = Executors.newSingleThreadExecutor()
        lastFrameNs = System.nanoTime()
        main.postDelayed(watchdog, 250)
        bindCamera()
        AirAccessibilityService.instance?.setRunning(true, controller.paused)
        return true
    }

    private fun bindCamera() {
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            val p = future.get()
            provider = p
            val facing = SettingsStore.extras.cameraFacing
            val selector = if (facing == "back") CameraSelector.DEFAULT_BACK_CAMERA else CameraSelector.DEFAULT_FRONT_CAMERA
            val analysis = ImageAnalysis.Builder()
                .setResolutionSelector(ResolutionSelector.Builder()
                    .setResolutionStrategy(ResolutionStrategy(Size(640, 480), ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER))
                    .build())
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                .build()
            analysis.setAnalyzer(analysisExecutor!!) { frame -> tracker?.analyze(frame, SettingsStore.extras.mirror) }
            try {
                p.unbindAll()
                p.bindToLifecycle(this, selector, analysis)
                boundFacing = facing
            } catch (e: Exception) {
                EngineBus.error = "Camera unavailable: ${e.message}"
                stopSelf()
            }
        }, { r -> main.post(r) })
    }

    /** Called on MediaPipe's result thread for every processed frame. */
    private fun onHand(pts: FloatArray?, w: Int, h: Int) {
        val t = now()
        lastFrameNs = System.nanoTime()
        if (lastResultNs != 0L) fps = 0.9 * fps + 0.1 / ((lastFrameNs - lastResultNs) / 1e9).coerceAtLeast(1e-3)
        lastResultNs = lastFrameNs
        synchronized(lock) {
            if (pts != null) controller.update(pts, w, h, t) else controller.lost(t)
            EngineBus.view = controller.view(t)
        }
        EngineBus.fps = fps
        if (controller.paused != lastShownPause) refreshUi()
    }

    // ------------------------------------------------------------ pause / stop
    private fun togglePauseInternal() {
        synchronized(lock) { if (controller.paused) controller.resume(now()) else controller.pause("Paused by you", now()) }
        refreshUi()
    }

    fun isPaused() = controller.paused

    private fun refreshUi() {
        lastShownPause = controller.paused
        EngineBus.view = synchronized(lock) { controller.view(now()) }
        AirAccessibilityService.instance?.setRunning(true, controller.paused)
        getSystemService(NotificationManager::class.java).notify(NOTIF_ID, buildNotification())
    }

    /** Settings changed in the UI: rebind the camera if the lens changed. */
    fun onSettingsChanged() {
        if (boundFacing.isNotEmpty() && boundFacing != SettingsStore.extras.cameraFacing) main.post { bindCamera() }
    }

    // ------------------------------------------------------------ notification
    private fun createChannel() {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(NotificationChannel(CHANNEL, "AirCursor running", NotificationManager.IMPORTANCE_LOW)
            .apply { description = "Shown while hand control is active" })
    }

    private fun action(code: Int, label: String, act: String): Notification.Action {
        val pi = PendingIntent.getService(this, code, Intent(this, AirCursorService::class.java).setAction(act),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        return Notification.Action.Builder(null, label, pi).build()
    }

    private fun buildNotification(): Notification {
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
        val paused = controller.paused
        return Notification.Builder(this, CHANNEL)
            .setSmallIcon(R.mipmap.ic_launcher)
            .setContentTitle(if (paused) "AirCursor is paused" else "AirCursor is active")
            .setContentText(if (paused) (controller.pauseReason.ifEmpty { "Tap Resume to continue" }) else "Hand control is on. Vol+ and Vol- together = pause.")
            .setContentIntent(open)
            .setOngoing(true)
            .addAction(action(1, if (paused) "Resume" else "Pause", ACTION_TOGGLE))
            .addAction(action(2, "Stop", ACTION_STOP))
            .build()
    }

    private fun startInForeground() {
        val n = buildNotification()
        if (Build.VERSION.SDK_INT >= 29) startForeground(NOTIF_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA)
        else startForeground(NOTIF_ID, n)
    }

    companion object {
        const val ACTION_TOGGLE = "com.aircursor.TOGGLE_PAUSE"
        const val ACTION_STOP = "com.aircursor.STOP"
        private const val CHANNEL = "aircursor_running"
        private const val NOTIF_ID = 1
        @Volatile var instance: AirCursorService? = null

        fun start(ctx: Context) {
            ctx.startForegroundService(Intent(ctx, AirCursorService::class.java))
        }

        fun stop(ctx: Context) {
            instance?.stopSelf() ?: ctx.stopService(Intent(ctx, AirCursorService::class.java))
        }

        /** Pause / resume from anywhere (panel, notification, hardware keys, JS). */
        fun togglePause() { instance?.togglePauseInternal() }
        fun pause() { instance?.let { if (!it.isPaused()) it.togglePauseInternal() } }
        fun resume() { instance?.let { if (it.isPaused()) it.togglePauseInternal() } }
    }
}
