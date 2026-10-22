package com.aircursor.engine

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.exp
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/** One-euro filter: smooth when slow (no jitter), responsive when fast. */
class OneEuro(var minCutoff: Double = 1.0, private val beta: Double = 0.02, private val dCutoff: Double = 1.0) {
    private var x = 0.0
    private var dx = 0.0
    private var t = -1.0

    fun reset() { t = -1.0 }

    private fun alpha(cutoff: Double, dt: Double): Double {
        val tau = 1.0 / (2 * PI * cutoff)
        return 1.0 / (1.0 + tau / dt)
    }

    fun filter(v: Double, now: Double): Double {
        if (t < 0) { x = v; dx = 0.0; t = now; return v }
        val dt = max(now - t, 1e-3)
        val aD = alpha(dCutoff, dt)
        dx = aD * (v - x) / dt + (1 - aD) * dx
        val a = alpha(minCutoff + beta * abs(dx), dt)
        x = a * v + (1 - a) * x
        t = now
        return x
    }
}

private fun smoothstep(v: Double): Double {
    val t = min(max(v, 0.0), 1.0)
    return t * t * (3 - 2 * t)
}

/**
 * Maps hand motion (camera px) to cursor motion (screen px): hand-size normalised, speeds up on
 * fast moves, and ramps up during long one-direction moves (so corners are easy to reach).
 */
class SmartMotion(private val basePx: Double) {
    private var size = -1.0
    var run = 0.0; private set
    private var dirX = 0.0
    private var dirY = 0.0
    private var hasDir = false
    private var slowT = 0.0
    var factor = 1.0; private set

    fun reset() { size = -1.0; run = 0.0; hasDir = false; slowT = 0.0; factor = 1.0 }

    /** Returns cursor displacement (x, y) in screen px. */
    fun map(dx: Double, dy: Double, dtIn: Double, handSize: Double, cfg: EngineSettings): DoubleArray {
        size = if (size < 0) handSize else 0.9 * size + 0.1 * handSize
        val dt = max(dtIn, 1e-3)
        val nx = dx / size
        val ny = dy / size
        val dist = hypot(nx, ny)
        if (dist * size < 0.6) {            // sub-pixel tremor: no motion, but time still passes
            slowT += dt
            if (slowT > 0.25) run = 0.0
            run *= exp(-dt / 2.0)
            factor = 1.0
            return doubleArrayOf(0.0, 0.0)
        }
        val speed = dist / dt                // hand lengths / s
        var gain = basePx * cfg.speed
        var f = 1.0
        if (cfg.smartMotion) {
            f *= 1 + cfg.accelStrength * smoothstep((speed - 0.25) / 2.75)
            val ux = nx / dist
            val uy = ny / dist
            if (!hasDir) {
                dirX = ux; dirY = uy; hasDir = true
            } else if (ux * dirX + uy * dirY < 0.35) {   // changed direction: restart the run
                run *= 0.25; dirX = ux; dirY = uy
            } else {
                val vx = 0.7 * dirX + 0.3 * ux
                val vy = 0.7 * dirY + 0.3 * uy
                val n = max(sqrt(vx * vx + vy * vy), 1e-6)
                dirX = vx / n; dirY = vy / n
            }
            if (speed > 0.3) { run += dist; slowT = 0.0 } else {
                slowT += dt
                if (slowT > 0.25) run = 0.0
            }
            run *= exp(-dt / 2.0)
            f *= 1 + cfg.longMoveBoost * smoothstep(run / 2.5)
        }
        factor = f
        return doubleArrayOf(nx * gain * f, ny * gain * f)
    }
}

/** Counts full circles drawn by a fingertip. Positive = clockwise on screen. */
class Dial {
    private val xs = ArrayDeque<Double>()
    private val ys = ArrayDeque<Double>()
    private var prev: Double? = null

    fun reset() { xs.clear(); ys.clear(); prev = null }

    fun update(tx: Double, ty: Double, size: Double): Double {
        xs.addLast(tx); ys.addLast(ty)
        if (xs.size > 10) { xs.removeFirst(); ys.removeFirst() }
        if (xs.size < 5) return 0.0
        val vx = tx - xs.average()
        val vy = ty - ys.average()
        if (hypot(vx, vy) < DIAL_MIN_RADIUS * size) { prev = null; return 0.0 }
        val ang = atan2(vy, vx)                // screen y points down, so + = clockwise
        val p = prev
        prev = ang
        if (p == null) return 0.0
        var da = (ang - p + PI) % (2 * PI)
        if (da < 0) da += 2 * PI
        da -= PI
        return if (abs(da) < 2.0) da / (2 * PI) else 0.0   // ignore tracking glitches
    }

    companion object { const val DIAL_MIN_RADIUS = 0.18 }
}
