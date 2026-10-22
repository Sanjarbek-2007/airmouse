package com.aircursor.engine

/** What the hand is doing. */
enum class Gesture(val id: String) {
    POINT("point"), PINCH("pinch"), TUCK("tuck"), PEACE("peace"), THREE("three"),
    ROCK("rock"), FIST("fist"), OPEN("open"), NONE("none");

    companion object {
        fun fromId(id: String): Gesture? = values().firstOrNull { it.id == id }
    }
}

/** What the phone does about it. TAP = touch down while held (quick = tap, hold+move = drag). */
enum class Action(val id: String) {
    NONE("none"), MOVE("move"), TAP("tap"), BACK("back"), HOME("home"), RECENTS("recents"),
    NOTIFICATIONS("notifications"), SCROLL("scroll"), FAST_SCROLL("fast_scroll"), VOLUME("volume");

    val isGlobal get() = this == BACK || this == HOME || this == RECENTS || this == NOTIFICATIONS
    val movesCursor get() = this == MOVE || this == TAP

    companion object {
        fun fromId(id: String): Action? = values().firstOrNull { it.id == id }
    }
}

enum class GlobalAction { BACK, HOME, RECENTS, NOTIFICATIONS }

val DEFAULT_MAPPING: Map<Gesture, Action> = mapOf(
    Gesture.POINT to Action.MOVE,
    Gesture.PINCH to Action.TAP,
    Gesture.TUCK to Action.BACK,
    Gesture.PEACE to Action.SCROLL,
    Gesture.THREE to Action.FAST_SCROLL,
    Gesture.ROCK to Action.VOLUME,
    Gesture.FIST to Action.NONE,
    Gesture.OPEN to Action.NONE,
)

/** User settings the engine reads every frame. Mirrors the desktop app's Config. */
class EngineSettings {
    var speed = 1.0
    var smartMotion = true
    var accelStrength = 0.0        // off by default: cursor follows the hand 1:1 (opt-in)
    var longMoveBoost = 0.0        // off by default (opt-in)
    var smoothing = 0.5
    var holdScale = 1.0
    var pinchSensitivity = 1.0
    var tuckSensitivity = 1.0
    var scrollSpeed = 1.0
    var volumeStep = 10.0          // percent per full finger circle
    var guardEnabled = true
    var guardClicks = 6
    var guardWindow = 2.0          // seconds
    var gestures: MutableMap<Gesture, Action> = DEFAULT_MAPPING.toMutableMap()

    fun actionFor(g: Gesture): Action =
        if (g == Gesture.NONE) Action.NONE else (gestures[g] ?: DEFAULT_MAPPING[g] ?: Action.NONE)
}

/** Everything the engine can make the phone do. Implemented by the accessibility service. */
interface ActionSink {
    /** Move the on-screen cursor by this many screen pixels. */
    fun moveBy(dx: Float, dy: Float)
    /** Touch down / up at the cursor (quick pair = tap, down + moveBy... + up = drag). */
    fun pressDown()
    fun pressUp()
    /** Wheel-style scroll: +dy = reveal content above (finger swipes down), +dx = reveal right. */
    fun scroll(dx: Int, dy: Int)
    fun global(action: GlobalAction)
    fun volumeGet(): Float
    fun volumeSet(v: Float)
    /** Drop any queued cursor motion (called on pause). */
    fun cancelMotion()
}

/** Snapshot for the UI. */
data class EngineView(
    val label: String = "NO HAND",
    val gesture: String = Gesture.NONE.id,
    val action: String = Action.NONE.id,
    val pending: String? = null,
    val progress: Double = 0.0,
    val pinch: Double = 1.0,
    val tuck: Double = 1.0,
    val volume: Double = 0.0,
    val factor: Double = 1.0,
    val hand: Boolean = false,
    val paused: Boolean = false,
    val pauseReason: String = "",
)
