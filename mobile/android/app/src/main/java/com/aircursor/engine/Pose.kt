package com.aircursor.engine

import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.min

class Pose(
    val gesture: Gesture,
    val size: Double,         // wrist -> middle knuckle, camera px
    val motionSize: Double,   // steadier hand scale for motion normalisation
    val pinch: Double,        // thumb-index distance / size
    val tuck: Double,         // thumb-to-knuckle distance / size
)

/**
 * Turns 21 hand landmarks (x0,y0,x1,y1,... normalised 0..1) into a [Gesture]. Keeps per-finger
 * hysteresis so a finger on the edge of "extended" doesn't flicker.
 */
class PoseClassifier {
    private val ext = BooleanArray(4)

    fun classify(pts: FloatArray, w: Int, h: Int, current: Gesture,
                 pinchSens: Double = 1.0, tuckSens: Double = 1.0): Pose {
        fun d(a: Int, b: Int) = hypot((pts[a * 2] - pts[b * 2]).toDouble() * w, (pts[a * 2 + 1] - pts[b * 2 + 1]).toDouble() * h)
        val size = max(d(0, 9), 1.0)
        val motionSize = max((d(0, 9) + d(5, 17)) / 2, 1.0)
        for (i in 0 until 4) {
            val ratio = d(TIPS[i], 0) / max(d(PIPS[i], 0), 1.0)
            ext[i] = ratio > (if (ext[i]) 1.0 else 1.15)
        }
        val idx = ext[0]; val mid = ext[1]; val ring = ext[2]; val pinky = ext[3]
        val pinch = d(4, 8) / size
        val tuck = min(d(4, 9), min(d(4, 13), d(4, 17))) / size
        val pinchThr = (if (current == Gesture.PINCH) PINCH_OFF else PINCH_ON) * pinchSens
        val tuckThr = (if (current == Gesture.TUCK) TUCK_OFF else TUCK_ON) * tuckSens

        val g = when {
            !ext.any { it } -> Gesture.FIST          // checked first: a fist can never count as a pinch
            pinch < pinchThr -> Gesture.PINCH
            ext.all { it } && tuck < tuckThr -> Gesture.TUCK
            idx && pinky && !mid && !ring -> Gesture.ROCK
            idx && mid && ring && !pinky -> Gesture.THREE
            idx && mid && !ring && !pinky -> Gesture.PEACE
            idx && !mid -> Gesture.POINT
            else -> Gesture.OPEN
        }
        return Pose(g, size, motionSize, pinch, tuck)
    }

    companion object {
        val TIPS = intArrayOf(8, 12, 16, 20)
        val PIPS = intArrayOf(6, 10, 14, 18)
        const val PINCH_ON = 0.30
        const val PINCH_OFF = 0.42
        const val TUCK_ON = 0.55
        const val TUCK_OFF = 0.75
    }
}
