package com.aircursor.service

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.content.res.Configuration
import android.graphics.Path
import android.graphics.PixelFormat
import android.graphics.Rect
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.util.DisplayMetrics
import android.view.Choreographer
import android.view.Gravity
import android.view.KeyEvent
import android.view.WindowManager
import android.view.accessibility.AccessibilityEvent
import com.aircursor.engine.GlobalAction
import kotlin.math.abs
import kotlin.math.exp

/**
 * The phone-side "mouse driver". Android lets an accessibility service
 *  - draw over every app (the cursor + the safety panel),
 *  - inject touches (taps, drags, swipes) and
 *  - trigger Back / Home / Recents / Notifications.
 * It also sees the volume keys, which gives us a hardware emergency stop (Vol+ and Vol- together).
 *
 * All view / gesture work happens on the main thread; public methods are safe to call from any thread.
 */
class AirAccessibilityService : AccessibilityService() {
    private val main = Handler(Looper.getMainLooper())
    private lateinit var wm: WindowManager
    private var screen = Rect(0, 0, 1080, 1920)

    // --- overlays
    private var cursor: CursorView? = null
    private var cursorLp: WindowManager.LayoutParams? = null
    private var panel: PanelView? = null
    private var panelLp: WindowManager.LayoutParams? = null
    private var running = false
    private var paused = false

    // --- cursor position + glide
    private var cx = 0f
    private var cy = 0f
    private var pendX = 0f
    private var pendY = 0f
    private var gliding = false
    private var lastNs = 0L
    private val glide = object : Choreographer.FrameCallback {
        override fun doFrame(frameTimeNanos: Long) {
            val dt = ((frameTimeNanos - lastNs) / 1e9f).coerceIn(0.001f, 0.1f)
            lastNs = frameTimeNanos
            val k = 1f - exp(-dt / 0.04f)
            val mx = pendX * k
            val my = pendY * k
            pendX -= mx; pendY -= my
            cx = (cx + mx).coerceIn(screen.left.toFloat(), (screen.right - 1).toFloat())
            cy = (cy + my).coerceIn(screen.top.toFloat(), (screen.bottom - 1).toFloat())
            placeCursor()
            if (abs(pendX) > 0.2f || abs(pendY) > 0.2f) Choreographer.getInstance().postFrameCallback(this)
            else gliding = false
        }
    }

    // --- touch session (drag = a chain of continued strokes)
    private var touching = false
    private var upRequested = false
    private var pendingStart = false
    private var dispatching = false
    private var stroke: GestureDescription.StrokeDescription? = null
    private var lastX = 0f
    private var lastY = 0f
    private var swiping = false
    private var pendScrollX = 0
    private var pendScrollY = 0

    // --- hardware emergency stop
    private var volUpAt = 0L
    private var volDownAt = 0L

    private val dp get() = resources.displayMetrics.density

    // ------------------------------------------------------------- lifecycle
    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        SettingsStore.ensureLoaded(this)
        wm = getSystemService(WINDOW_SERVICE) as WindowManager
        screen = bounds()
        cx = screen.exactCenterX(); cy = screen.exactCenterY()
        running = AirCursorService.instance != null
        paused = AirCursorService.instance?.isPaused() ?: false
        rebuildOverlays()
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) { /* we only need gestures + overlays */ }
    override fun onInterrupt() { releaseEverything() }

    override fun onUnbind(intent: android.content.Intent?): Boolean {
        instance = null
        main.post { removeOverlays() }
        AirCursorService.instance?.let { AirCursorService.stop(this) }  // no driver => stop the camera too
        return super.onUnbind(intent)
    }

    override fun onConfigurationChanged(newConfig: Configuration) {
        super.onConfigurationChanged(newConfig)
        main.post {
            screen = bounds()
            cx = cx.coerceIn(0f, (screen.right - 1).toFloat()); cy = cy.coerceIn(0f, (screen.bottom - 1).toFloat())
            placeCursor()
        }
    }

    private fun bounds(): Rect {
        if (Build.VERSION.SDK_INT >= 30) return wm.maximumWindowMetrics.bounds
        val m = DisplayMetrics()
        @Suppress("DEPRECATION") wm.defaultDisplay.getRealMetrics(m)
        return Rect(0, 0, m.widthPixels, m.heightPixels)
    }

    // --------------------------------------------------------------- overlays
    private fun overlayParams(w: Int, h: Int, touchable: Boolean) = WindowManager.LayoutParams(
        w, h, WindowManager.LayoutParams.TYPE_ACCESSIBILITY_OVERLAY,
        WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN or
            WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS or
            (if (touchable) 0 else WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE),
        PixelFormat.TRANSLUCENT,
    ).apply { gravity = Gravity.TOP or Gravity.START }

    /** (Re)create overlays to match the current settings and running state. Main thread. */
    private fun rebuildOverlays() {
        removeOverlays()
        if (!running) return
        val prefs = SettingsStore.extras
        if (prefs.showCursor) {
            val size = (prefs.cursorSize * dp).toInt()
            cursor = CursorView(this).also { v ->
                v.mode = if (paused) CursorView.Mode.PAUSED else CursorView.Mode.NORMAL
                cursorLp = overlayParams(size, size, touchable = false)
                runCatching { wm.addView(v, cursorLp) }
            }
            placeCursor()
        }
        if (prefs.floatPanel) {
            panel = PanelView(this,
                onToggle = { AirCursorService.togglePause() },
                onStop = { AirCursorService.stop(this) },
                onDrag = { dx, dy -> panelLp?.let { lp -> lp.x += dx; lp.y += dy; panel?.let { p -> runCatching { wm.updateViewLayout(p, lp) } } } },
            ).also { v ->
                v.setPaused(paused)
                panelLp = overlayParams(WindowManager.LayoutParams.WRAP_CONTENT, WindowManager.LayoutParams.WRAP_CONTENT, touchable = true)
                    .apply { x = (screen.right - 260 * dp).toInt().coerceAtLeast(0); y = (72 * dp).toInt() }
                runCatching { wm.addView(v, panelLp) }
            }
        }
    }

    private fun removeOverlays() {
        cursor?.let { runCatching { wm.removeView(it) } }
        panel?.let { runCatching { wm.removeView(it) } }
        cursor = null; panel = null
    }

    private fun placeCursor() {
        val v = cursor ?: return
        val lp = cursorLp ?: return
        lp.x = (cx - lp.width / 2f).toInt(); lp.y = (cy - lp.height / 2f).toInt()
        runCatching { wm.updateViewLayout(v, lp) }
    }

    /** Called by the camera service when it starts / stops / pauses. */
    fun setRunning(isRunning: Boolean, isPaused: Boolean) = main.post {
        val changed = running != isRunning
        running = isRunning; paused = isPaused
        if (changed) rebuildOverlays() else {
            cursor?.mode = if (paused) CursorView.Mode.PAUSED else CursorView.Mode.NORMAL
            panel?.setPaused(paused)
        }
        if (!isRunning || isPaused) releaseEverything()
    }

    fun applySettings() = main.post { rebuildOverlays() }

    // ----------------------------------------------------------- cursor motion
    fun moveCursorBy(dx: Float, dy: Float) {
        main.post {
            pendX += dx; pendY += dy
            if (!gliding) {
                gliding = true; lastNs = System.nanoTime()
                Choreographer.getInstance().postFrameCallback(glide)
            }
        }
    }

    fun cancelMotion() { main.post { pendX = 0f; pendY = 0f } }

    // -------------------------------------------------------------------- touch
    fun touchDown() {
        main.post {
            if (touching) return@post
            touching = true; upRequested = false
            cursor?.mode = CursorView.Mode.PRESSED
            if (dispatching) pendingStart = true else startStroke()
        }
    }

    fun touchUp() {
        main.post {
            if (!touching) return@post
            upRequested = true
            cursor?.mode = if (paused) CursorView.Mode.PAUSED else CursorView.Mode.NORMAL
            if (!dispatching && !pendingStart) continueStroke()
        }
    }

    private val strokeCallback = object : GestureResultCallback() {
        override fun onCompleted(gestureDescription: GestureDescription?) {
            dispatching = false
            when {
                pendingStart -> { pendingStart = false; startStroke() }
                touching -> continueStroke()
            }
        }

        override fun onCancelled(gestureDescription: GestureDescription?) {
            dispatching = false; touching = false; stroke = null; pendingStart = false
            cursor?.mode = if (paused) CursorView.Mode.PAUSED else CursorView.Mode.NORMAL
        }
    }

    private fun startStroke() {
        lastX = cx; lastY = cy
        val s = GestureDescription.StrokeDescription(Path().apply { moveTo(cx, cy) }, 0, STROKE_MS, true)
        stroke = s
        dispatching = true
        if (!dispatchGesture(GestureDescription.Builder().addStroke(s).build(), strokeCallback, null)) {
            dispatching = false; touching = false; stroke = null
        }
    }

    private fun continueStroke() {
        val prev = stroke ?: run { touching = false; return }
        val isLast = upRequested                       // finger lifts with this stroke
        val p = Path().apply { moveTo(lastX, lastY); lineTo(cx, cy) }
        val next = prev.continueStroke(p, 0, STROKE_MS, !isLast)
        lastX = cx; lastY = cy
        stroke = if (isLast) null else next
        if (isLast) touching = false
        dispatching = true
        if (!dispatchGesture(GestureDescription.Builder().addStroke(next).build(), strokeCallback, null)) {
            dispatching = false; touching = false; stroke = null
        }
    }

    private fun releaseEverything() {
        pendScrollX = 0; pendScrollY = 0; pendX = 0f; pendY = 0f
        if (touching) { upRequested = true; if (!dispatching) continueStroke() }
        cursor?.mode = if (paused) CursorView.Mode.PAUSED else CursorView.Mode.NORMAL
    }

    // ------------------------------------------------------------------- scroll
    fun scrollBy(dx: Int, dy: Int) {
        main.post {
            pendScrollX = (pendScrollX + dx).coerceIn(-6, 6)
            pendScrollY = (pendScrollY + dy).coerceIn(-6, 6)
            if (!swiping && !touching) flushScroll()
        }
    }

    private fun flushScroll() {
        val nx = pendScrollX; val ny = pendScrollY
        pendScrollX = 0; pendScrollY = 0
        if (nx == 0 && ny == 0) return
        val step = screen.height() * 0.11f
        // wheel +dy = reveal content above = finger swipes DOWN; +dx = reveal right = finger swipes LEFT
        val ex = (cx - nx * step).coerceIn(screen.left + 4f, screen.right - 4f)
        val ey = (cy + ny * step).coerceIn(screen.top + 4f, screen.bottom - 4f)
        if (abs(ex - cx) < 8f && abs(ey - cy) < 8f) return
        val path = Path().apply { moveTo(cx, cy); lineTo(ex, ey) }
        val g = GestureDescription.Builder().addStroke(GestureDescription.StrokeDescription(path, 0, 140)).build()
        swiping = true
        val ok = dispatchGesture(g, object : GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) { swiping = false; if (pendScrollX != 0 || pendScrollY != 0) flushScroll() }
            override fun onCancelled(gestureDescription: GestureDescription?) { swiping = false }
        }, null)
        if (!ok) swiping = false
    }

    // ------------------------------------------------------------------- global
    fun performGlobal(a: GlobalAction) {
        main.post {
            performGlobalAction(when (a) {
                GlobalAction.BACK -> GLOBAL_ACTION_BACK
                GlobalAction.HOME -> GLOBAL_ACTION_HOME
                GlobalAction.RECENTS -> GLOBAL_ACTION_RECENTS
                GlobalAction.NOTIFICATIONS -> GLOBAL_ACTION_NOTIFICATIONS
            })
        }
    }

    // ------------------------------------------------- hardware emergency stop
    /** Volume Up + Volume Down pressed together = pause/resume. Only active while AirCursor runs. */
    override fun onKeyEvent(event: KeyEvent): Boolean {
        if (AirCursorService.instance == null || event.action != KeyEvent.ACTION_DOWN) return false
        val now = System.currentTimeMillis()
        when (event.keyCode) {
            KeyEvent.KEYCODE_VOLUME_UP -> volUpAt = now
            KeyEvent.KEYCODE_VOLUME_DOWN -> volDownAt = now
            else -> return false
        }
        if (volUpAt > 0 && volDownAt > 0 && abs(volUpAt - volDownAt) < 700) {
            volUpAt = 0; volDownAt = 0
            AirCursorService.togglePause()
            return true
        }
        return false
    }

    companion object {
        @Volatile var instance: AirAccessibilityService? = null
        private const val STROKE_MS = 40L
    }
}
