package com.aircursor.engine

import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Turns hand poses into phone actions. Same safety design as the desktop app:
 *  - confirmation: a new gesture must persist (and for >= 2 frames) before it counts
 *  - the cursor freezes while a different gesture is being confirmed
 *  - a hand lost for 0.3 s releases everything; shorter dropouts keep a drag alive
 *  - pause() instantly releases the touch and drops queued motion
 *  - click-storm guard: too many presses in a short window auto-pauses
 *
 * Not thread-safe by itself: callers synchronise (the service calls it from one thread and
 * uses [synchronized] for pause/resume from the UI).
 */
class Controller(
    val cfg: EngineSettings,
    private val sink: ActionSink,
    baseScalePx: Double,
    var onTrip: ((String) -> Unit)? = null,
) {
    private val classifier = PoseClassifier()
    private val fx = OneEuro()
    private val fy = OneEuro()
    private val motion = SmartMotion(baseScalePx)
    private val dial = Dial()

    var paused = false; private set
    var pauseReason = ""; private set
    private val pressTimes = ArrayDeque<Double>()

    var stable = Gesture.NONE; private set
    private var since = 0.0
    private var cand: Gesture? = null
    private var candT = 0.0
    private var candN = 0
    private var raw = Gesture.NONE
    private var freezeUntil = 0.0
    private var flashText = ""
    private var flashUntil = 0.0
    private var hasPrev = false
    private var prevX = 0.0
    private var prevY = 0.0
    private var prevT = 0.0
    private var hasScroll = false
    private var scrollX = 0.0
    private var scrollY = 0.0
    private var accX = 0.0
    private var accY = 0.0
    private var slideAxis = ""
    private var vol = 0.5
    private var pose: Pose? = null
    private var touching = false

    init { resetState(0.0) }

    private fun resetState(now: Double) {
        stable = Gesture.NONE; since = now; cand = null; candT = 0.0; candN = 0; raw = Gesture.NONE
        freezeUntil = 0.0; flashText = ""; flashUntil = 0.0
        hasPrev = false; prevT = now; hasScroll = false; accX = 0.0; accY = 0.0
        slideAxis = ""; vol = 0.5
        fx.reset(); fy.reset(); motion.reset(); dial.reset()
    }

    // ------------------------------------------------------------------ pause
    /** Instant stop: lift the touch and drop queued cursor motion. */
    fun pause(reason: String, now: Double) {
        paused = true; pauseReason = reason
        releaseTouch()
        sink.cancelMotion()
        resetState(now)
    }

    fun resume(now: Double) {
        paused = false; pauseReason = ""
        pressTimes.clear()
        resetState(now)
    }

    fun shutdown() { releaseTouch(); sink.cancelMotion() }

    private fun releaseTouch() { if (touching) { touching = false; sink.pressUp() } }

    // ----------------------------------------------------------- confirmation
    val action: Action get() = if (stable == Gesture.NONE) Action.NONE else cfg.actionFor(stable)

    private fun confirmTime(g: Gesture): Double =
        if (g == Gesture.NONE) NO_HAND_CONFIRM else confirmBase(cfg.actionFor(g)) * cfg.holdScale

    private fun confirmBase(a: Action) = when (a) {
        Action.MOVE -> 0.10; Action.TAP -> 0.10
        Action.BACK, Action.HOME, Action.RECENTS, Action.NOTIFICATIONS -> 0.20
        Action.SCROLL, Action.FAST_SCROLL -> 0.12
        Action.VOLUME -> 0.25
        Action.NONE -> 0.10
    }

    fun candProgress(now: Double): Double? = cand?.let { min((now - candT) / confirmTime(it), 1.0) }

    private fun advance(g: Gesture, now: Double) {
        raw = g
        if (g == stable) { cand = null; return }
        if (g != cand) { cand = g; candT = now; candN = 1 } else candN++
        if (now - candT >= confirmTime(g) && candN >= MIN_FRAMES) switchTo(g, now)
    }

    private fun switchTo(new: Gesture, now: Double) {
        val old = action
        val held = now - since
        if (old == Action.TAP) {
            releaseTouch()
            if (held < HOLD_LABEL) { flashText = "TAP"; flashUntil = now + 0.4 }
        }
        stable = new; since = now; cand = null
        when (val a = action) {
            Action.TAP -> {
                touching = true; sink.pressDown()
                freezeUntil = now + CLICK_FREEZE
                recordPress(now)
            }
            Action.BACK, Action.HOME, Action.RECENTS, Action.NOTIFICATIONS -> {
                sink.global(when (a) {
                    Action.BACK -> GlobalAction.BACK
                    Action.HOME -> GlobalAction.HOME
                    Action.RECENTS -> GlobalAction.RECENTS
                    else -> GlobalAction.NOTIFICATIONS
                })
                flashText = a.id.uppercase(); flashUntil = now + 0.6
                recordPress(now)
            }
            Action.VOLUME -> { vol = sink.volumeGet().toDouble(); dial.reset() }
            else -> {}
        }
        hasScroll = false
    }

    private fun recordPress(now: Double) {
        pressTimes.addLast(now)
        while (pressTimes.isNotEmpty() && now - pressTimes.first() > cfg.guardWindow) pressTimes.removeFirst()
        if (cfg.guardEnabled && pressTimes.size >= cfg.guardClicks) {
            val reason = "Safety guard: ${pressTimes.size} presses in ${cfg.guardWindow.toInt()}s"
            pause(reason, now)
            onTrip?.invoke(reason)
        }
    }

    // ----------------------------------------------------------------- frames
    /** No hand in view this frame. */
    fun lost(now: Double): String {
        pose = null; hasPrev = false; fx.reset(); fy.reset()
        if (!paused) advance(Gesture.NONE, now)
        return label(now)
    }

    /** pts: 21 landmarks as x0,y0,... in 0..1 (already mirrored/rotated upright). */
    fun update(pts: FloatArray, w: Int, h: Int, now: Double): String {
        val p = classifier.classify(pts, w, h, stable, cfg.pinchSensitivity, cfg.tuckSensitivity)
        pose = p
        if (paused) return label(now)
        advance(p.gesture, now)

        val cutoff = 0.4 + 2.0 * (1 - cfg.smoothing)
        fx.minCutoff = cutoff; fy.minCutoff = cutoff
        val px = (pts[5 * 2] + pts[9 * 2]) / 2.0 * w          // palm point: stable under finger curls
        val py = (pts[5 * 2 + 1] + pts[9 * 2 + 1]) / 2.0 * h
        val fpx = fx.filter(px, now)
        val fpy = fy.filter(py, now)
        val active = raw == stable
        val act = action

        if (act.movesCursor && active && now >= freezeUntil && hasPrev) {
            val d = motion.map(fpx - prevX, fpy - prevY, now - prevT, p.motionSize, cfg)
            if (d[0] != 0.0 || d[1] != 0.0) sink.moveBy(d[0].toFloat(), d[1].toFloat())
        }
        if ((act == Action.SCROLL || act == Action.FAST_SCROLL) && active) {
            slide(fpx, fpy, p.motionSize, if (act == Action.FAST_SCROLL) FAST_SCROLL else 1)
        } else hasScroll = false
        if (act == Action.VOLUME && active) {
            val turns = dial.update(pts[8 * 2].toDouble() * w, pts[8 * 2 + 1].toDouble() * h, p.size)
            if (turns != 0.0) {
                vol = min(max(vol + cfg.volumeStep / 100 * turns, 0.0), 1.0)
                sink.volumeSet(vol.toFloat())
            }
        }
        hasPrev = true; prevX = fpx; prevY = fpy; prevT = now
        return label(now)
    }

    private fun slide(x: Double, y: Double, size: Double, speed: Int) {
        slideAxis = ""
        if (hasScroll) {
            val dx = (x - scrollX) / size
            val dy = (y - scrollY) / size
            if (max(abs(dx), abs(dy)) > SCROLL_DEADZONE) {
                val horizontal = abs(dy) <= abs(dx)
                val k = SCROLL_PER_HAND * cfg.scrollSpeed * speed
                if (horizontal) accX += dx * k else accY += -dy * k
                slideAxis = if (horizontal) " <>" else " ^v"
            }
            val nx = accX.toInt(); val ny = accY.toInt()
            if (nx != 0 || ny != 0) { sink.scroll(nx, ny); accX -= nx; accY -= ny }
        }
        hasScroll = true; scrollX = x; scrollY = y
    }

    // ------------------------------------------------------------------ views
    fun label(now: Double): String {
        if (paused) return "PAUSED"
        val act = action
        if (stable == Gesture.NONE) return if (now < flashUntil) flashText else "NO HAND"
        if (act != Action.TAP && now < flashUntil) return flashText
        val held = now - since
        return when (act) {
            Action.TAP -> if (held > HOLD_LABEL) "TOUCH HOLD (drag)" else "TAP"
            Action.MOVE -> "MOVE"
            Action.SCROLL -> "SLIDE$slideAxis"
            Action.FAST_SCROLL -> "FAST SLIDE$slideAxis"
            Action.VOLUME -> "VOLUME ${Math.round(vol * 100)}%"
            Action.BACK, Action.HOME, Action.RECENTS, Action.NOTIFICATIONS -> act.id.uppercase()
            Action.NONE -> "IDLE"
        }
    }

    fun view(now: Double): EngineView {
        val ps = pose
        return EngineView(
            label = label(now), gesture = stable.id, action = action.id,
            pending = cand?.id, progress = candProgress(now) ?: 0.0,
            pinch = ps?.pinch ?: 1.0, tuck = ps?.tuck ?: 1.0, volume = vol, factor = motion.factor,
            hand = ps != null, paused = paused, pauseReason = pauseReason,
        )
    }

    companion object {
        const val NO_HAND_CONFIRM = 0.30
        const val MIN_FRAMES = 2
        const val CLICK_FREEZE = 0.15
        const val HOLD_LABEL = 0.35
        const val SCROLL_PER_HAND = 4.0
        const val SCROLL_DEADZONE = 0.03
        const val FAST_SCROLL = 3
    }
}
