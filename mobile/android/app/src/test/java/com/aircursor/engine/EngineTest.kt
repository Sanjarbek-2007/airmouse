package com.aircursor.engine

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.sin

private const val W = 1280
private const val H = 720
private const val BASE = 700.0   // same scale as the desktop tests so numbers are comparable

class FakeSink : ActionSink {
    val log = mutableListOf<String>()
    var mx = 0.0
    var my = 0.0
    var vol = 0.30f
    val volSets = mutableListOf<Float>()
    var down = false
    override fun moveBy(dx: Float, dy: Float) { mx += dx; my += dy }
    override fun pressDown() { if (!down) { down = true; log += "down" } }
    override fun pressUp() { if (down) { down = false; log += "up" } }
    override fun scroll(dx: Int, dy: Int) { if (dy != 0) log += "scrollV:$dy"; if (dx != 0) log += "scrollH:$dx" }
    override fun global(action: GlobalAction) { log += "global:$action" }
    override fun volumeGet() = vol
    override fun volumeSet(v: Float) { volSets += v }
    override fun cancelMotion() { log += "cancel" }
    fun touches() = log.filter { it == "down" || it == "up" }
}

/** Synthetic upright hand. up = extended fingers (0 index, 1 middle, 2 ring, 3 pinky). */
fun hand(up: Set<Int>, ox: Double = 0.5, oy: Double = 0.75, thumb: String = "out",
         tipDx: Double = 0.0, tipDy: Double = 0.0): FloatArray {
    val s = 0.17
    val sx = H.toDouble() / W
    val p = Array(21) { DoubleArray(2) }
    p[0] = doubleArrayOf(ox, oy)
    val knuckles = listOf(5 to -0.05, 9 to 0.0, 13 to 0.045, 17 to 0.09)
    knuckles.forEachIndexed { f, (k, dx) ->
        val bx = ox + dx * sx; val by = oy - s
        p[k] = doubleArrayOf(bx, by)
        p[k + 1] = doubleArrayOf(bx, by - 0.06)
        if (f in up) { p[k + 2] = doubleArrayOf(bx, by - 0.11); p[k + 3] = doubleArrayOf(bx, by - 0.16) }
        else { p[k + 2] = doubleArrayOf(bx, by - 0.03); p[k + 3] = doubleArrayOf(bx, by) }
    }
    p[1] = doubleArrayOf(ox - 0.06 * sx, oy - 0.05); p[2] = doubleArrayOf(ox - 0.10 * sx, oy - 0.10)
    p[3] = doubleArrayOf(ox - 0.13 * sx, oy - 0.13); p[4] = doubleArrayOf(ox - 0.17 * sx, oy - 0.17)
    when (thumb) {
        "pinch" -> p[4] = doubleArrayOf(p[8][0] + 0.004 * sx, p[8][1] + 0.004)
        "tuck" -> p[4] = doubleArrayOf(p[13][0], p[13][1] + 0.04)
    }
    p[8] = doubleArrayOf(p[8][0] + tipDx, p[8][1] + tipDy)
    return FloatArray(42) { i -> p[i / 2][i % 2].toFloat() }
}

val OPEN = hand(setOf(0, 1, 2, 3))
val FIST = hand(emptySet(), thumb = "pinch")   // thumb resting on index: must NOT tap
val POINT = hand(setOf(0))
val PINCH = hand(setOf(1, 2, 3), thumb = "pinch")
val TUCK = hand(setOf(0, 1, 2, 3), thumb = "tuck")

class Rig(configure: EngineSettings.() -> Unit = {}) {
    val cfg = EngineSettings().apply(configure)
    val sink = FakeSink()
    val c = Controller(cfg, sink, BASE)
    var t = 1000.0
    fun run(seq: List<FloatArray?>, dt: Double = 1.0 / 15) {
        for (f in seq) { t += dt; if (f == null) c.lost(t) else c.update(f, W, H, t) }
    }
}

fun rep(f: FloatArray?, n: Int) = List(n) { f }
fun circle(turns: Int, cw: Boolean = true, nPer: Int = 14): List<FloatArray> = List(turns * nPer) { i ->
    val a = 2 * PI * i / nPer * (if (cw) 1 else -1)
    hand(setOf(0, 3), tipDx = 0.06 * cos(a) * H / W, tipDy = 0.06 * sin(a))
}

class EngineTest {
    @Test fun fistNeverTapsEvenWithThumbOnIndex() {
        val r = Rig(); r.run(rep(POINT, 4) + rep(FIST, 12))
        assertTrue(r.sink.touches().isEmpty())
    }

    @Test fun pinchTaps() {
        val r = Rig(); r.run(rep(POINT, 4) + rep(PINCH, 5) + rep(POINT, 4))
        assertEquals(listOf("down", "up"), r.sink.touches())
    }

    @Test fun singleFrameGlitchIgnored() {
        val r = Rig(); r.run(rep(POINT, 4) + listOf(PINCH) + rep(POINT, 4))
        assertTrue(r.sink.touches().isEmpty())
    }

    @Test fun dragMovesCursorWhileHeld() {
        val r = Rig()
        r.run(rep(POINT, 3) + rep(PINCH, 4) + (1..11).map { hand(setOf(1, 2, 3), ox = 0.5 + 0.01 * it, thumb = "pinch") } + rep(POINT, 4))
        assertEquals(listOf("down", "up"), r.sink.touches())
        assertTrue(r.sink.mx > 100)
    }

    @Test fun movementIndependentOfHandPosition() {
        val res = listOf(0.25 to 0.8, 0.7 to 0.6).map { (ox, oy) ->
            val r = Rig(); r.run((0 until 25).map { hand(setOf(0), ox = ox + 0.004 * it, oy = oy) }); r.sink.mx
        }
        assertTrue(res[0] > 50 && abs(res[0] - res[1]) / res[0] < 0.1)
    }

    @Test fun openPalmLiftsTheMouse() {
        val r = Rig(); r.run(rep(POINT, 4) + (0 until 12).map { hand(setOf(0, 1, 2, 3), ox = 0.3 + 0.02 * it) })
        val before = r.sink.mx
        r.run((0 until 10).map { hand(setOf(0, 1, 2, 3), ox = 0.5 + 0.01 * it) })
        assertEquals(before, r.sink.mx, 1e-6)
    }

    private fun sweep(cfg: EngineSettings.() -> Unit): List<Double> {
        val r = Rig(cfg); val g = mutableListOf<Double>()
        for (i in 0 until 60) { r.t += 1.0 / 15; val b = r.sink.mx; r.c.update(hand(setOf(0), ox = 0.2 + 0.006 * i), W, H, r.t); g += r.sink.mx - b }
        return g
    }

    @Test fun defaultsAreAPlainOneToOneCursor() {
        assertEquals(0.0, EngineSettings().accelStrength, 0.0); assertEquals(0.0, EngineSettings().longMoveBoost, 0.0)
        val g = sweep {}
        assertTrue(abs(g.subList(45, 60).average() - g.subList(8, 16).average()) / g.subList(8, 16).average() < 0.1)
    }

    @Test fun fastSpeedUpWhenEnabled() {
        val slow = sweep { accelStrength = 1.0 }.subList(10, 30).average()
        val r = Rig { accelStrength = 1.0 }; val fast = mutableListOf<Double>()
        for (i in 0 until 40) { r.t += 1.0 / 15; val b = r.sink.mx; r.c.update(hand(setOf(0), ox = 0.2 + 0.02 * i), W, H, r.t); fast += r.sink.mx - b }
        assertTrue(fast.subList(10, 30).average() > 3.3 * slow)
    }

    @Test fun longReachBoostKeepsRampingUpWhenEnabled() {
        val g = sweep { longMoveBoost = 0.8 }
        assertTrue(g.subList(45, 60).average() > 1.4 * g.subList(8, 16).average())
    }

    @Test fun constantSpeedWhenSmartMotionOff() {
        val g = sweep { smartMotion = false }
        assertTrue(abs(g.subList(45, 60).average() - g.subList(8, 16).average()) / g.subList(8, 16).average() < 0.1)
    }

    @Test fun peaceSlidesBothAxes() {
        var r = Rig(); r.run((0 until 14).map { hand(setOf(0, 1), oy = 0.75 - 0.01 * it) })
        assertTrue(r.sink.log.any { it.startsWith("scrollV:") && it.removePrefix("scrollV:").toInt() > 0 })
        r = Rig(); r.run((0 until 14).map { hand(setOf(0, 1), ox = 0.3 + 0.012 * it) })
        assertTrue(r.sink.log.any { it.startsWith("scrollH:") })
    }

    @Test fun volumeDialBothDirections() {
        var r = Rig(); r.run(rep(hand(setOf(0, 3)), 6) + circle(2))
        assertTrue(r.sink.volSets.isNotEmpty() && r.sink.volSets.last() > 0.30f + 0.12f)
        r = Rig(); r.run(rep(hand(setOf(0, 3)), 6) + circle(1, cw = false))
        assertTrue(r.sink.volSets.isNotEmpty() && r.sink.volSets.last() < 0.30f - 0.05f)
    }

    @Test fun dropoutKeepsTouchButLongLossReleases() {
        var r = Rig(); r.run(rep(POINT, 3) + rep(PINCH, 4) + rep(null, 2) + rep(PINCH, 3))
        assertEquals(listOf("down"), r.sink.touches())
        r = Rig(); r.run(rep(POINT, 3) + rep(PINCH, 4) + rep(null, 10))
        assertEquals(listOf("down", "up"), r.sink.touches())
    }

    @Test fun pauseLiftsTouchAndBlocksActions() {
        val r = Rig(); r.run(rep(POINT, 3) + rep(PINCH, 5))
        assertEquals(listOf("down"), r.sink.touches())
        r.c.pause("test", r.t)
        assertEquals(listOf("down", "up"), r.sink.touches()); assertTrue("cancel" in r.sink.log)
        val n = r.sink.log.size
        r.run(rep(PINCH, 6) + rep(POINT, 6))
        assertEquals(n, r.sink.log.size); assertEquals("PAUSED", r.c.label(r.t))
        r.c.resume(r.t); r.run(rep(POINT, 6))
        assertEquals(Gesture.POINT, r.c.stable)
    }

    @Test fun clickStormGuardAutoPauses() {
        val r = Rig(); var tripped = ""
        r.c.onTrip = { tripped = it }
        val seq = mutableListOf<FloatArray?>(); repeat(10) { seq += rep(POINT, 5) + rep(PINCH, 5) }
        r.run(seq, dt = 1.0 / 30)
        assertTrue(r.c.paused && tripped.isNotEmpty())
        assertFalse(r.sink.down)
        assertTrue(r.sink.touches().count { it == "down" } <= 6)
    }

    @Test fun guardCanBeDisabled() {
        val r = Rig { guardEnabled = false }
        val seq = mutableListOf<FloatArray?>(); repeat(10) { seq += rep(POINT, 5) + rep(PINCH, 5) }
        r.run(seq, dt = 1.0 / 30)
        assertFalse(r.c.paused)
    }

    @Test fun thumbTuckIsBackByDefaultAndRemappable() {
        var r = Rig(); r.run(rep(OPEN, 3) + rep(TUCK, 8) + rep(OPEN, 4))
        assertEquals(1, r.sink.log.count { it == "global:BACK" })
        r = Rig { gestures[Gesture.TUCK] = Action.HOME }
        r.run(rep(OPEN, 3) + rep(TUCK, 8) + rep(OPEN, 4))
        assertEquals(1, r.sink.log.count { it == "global:HOME" })
    }

    @Test fun holdScaleSlowsConfirmation() {
        val r = Rig { holdScale = 2.5 }
        r.run(rep(POINT, 4) + rep(PINCH, 3))
        assertTrue(r.sink.touches().isEmpty())
    }
}
