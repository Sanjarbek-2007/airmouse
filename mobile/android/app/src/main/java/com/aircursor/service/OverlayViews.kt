package com.aircursor.service

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.drawable.GradientDrawable
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.ViewConfiguration
import android.widget.LinearLayout
import android.widget.TextView

/** The on-screen cursor: a ring + dot. Never intercepts touches. */
class CursorView(context: Context) : View(context) {
    enum class Mode { NORMAL, PRESSED, PAUSED }

    var mode = Mode.NORMAL
        set(v) { if (field != v) { field = v; invalidate() } }
    private val ring = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE }
    private val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.FILL }
    private val halo = Paint(Paint.ANTI_ALIAS_FLAG).apply { style = Paint.Style.STROKE; color = Color.argb(140, 0, 0, 0) }

    override fun onDraw(canvas: Canvas) {
        val c = when (mode) {
            Mode.NORMAL -> Color.parseColor("#19D3FF")
            Mode.PRESSED -> Color.parseColor("#2BD67B")
            Mode.PAUSED -> Color.parseColor("#FFB020")
        }
        val cx = width / 2f
        val cy = height / 2f
        val r = width / 2f - 4f
        ring.color = c; ring.strokeWidth = width * 0.09f
        halo.strokeWidth = ring.strokeWidth + 3f
        canvas.drawCircle(cx, cy, r, halo)
        canvas.drawCircle(cx, cy, r, ring)
        fill.color = c
        canvas.drawCircle(cx, cy, if (mode == Mode.PRESSED) r * 0.55f else r * 0.2f, fill)
    }
}

/**
 * The always-on-top safety panel: [Pause/Resume] [Stop]. Draggable by its body.
 * Lives in an accessibility overlay window so it stays above every app.
 */
class PanelView(
    context: Context,
    private val onToggle: () -> Unit,
    private val onStop: () -> Unit,
    private val onDrag: (dx: Int, dy: Int) -> Unit,
) : LinearLayout(context) {
    private val state = TextView(context)
    private val pause = TextView(context)
    private val stop = TextView(context)
    private var downX = 0f
    private var downY = 0f
    private var dragging = false
    private val slop = ViewConfiguration.get(context).scaledTouchSlop
    private val dp = context.resources.displayMetrics.density

    init {
        orientation = HORIZONTAL
        gravity = Gravity.CENTER_VERTICAL
        val pad = (10 * dp).toInt()
        setPadding(pad, (6 * dp).toInt(), pad, (6 * dp).toInt())
        background = pill(Color.parseColor("#EE0A0E14"), Color.parseColor("#2BD67B"), 18f)
        state.setTextColor(Color.parseColor("#2BD67B")); state.textSize = 12f
        state.setTypeface(state.typeface, android.graphics.Typeface.BOLD)
        addView(state, LayoutParams(LayoutParams.WRAP_CONTENT, LayoutParams.WRAP_CONTENT).apply { rightMargin = pad })
        styleButton(pause, "#FFB020", "#2A2110"); pause.setOnClickListener { onToggle() }
        styleButton(stop, "#FF4D5E", "#2B1217"); stop.text = "✕"; stop.setOnClickListener { onStop() }
        addView(pause, btnParams()); addView(stop, btnParams())
        setPaused(false)
    }

    private fun btnParams() = LayoutParams((40 * dp).toInt(), (34 * dp).toInt()).apply { leftMargin = (6 * dp).toInt() }

    private fun pill(fill: Int, stroke: Int, radiusDp: Float) = GradientDrawable().apply {
        setColor(fill); setStroke((1.5f * dp).toInt(), stroke); cornerRadius = radiusDp * dp
    }

    private fun styleButton(v: TextView, fg: String, bg: String) {
        v.gravity = Gravity.CENTER; v.textSize = 16f; v.setTextColor(Color.parseColor(fg))
        v.background = pill(Color.parseColor(bg), Color.parseColor(fg), 10f)
    }

    fun setPaused(paused: Boolean) {
        state.text = if (paused) "PAUSED" else "ACTIVE"
        state.setTextColor(Color.parseColor(if (paused) "#FFB020" else "#2BD67B"))
        pause.text = if (paused) "▶" else "⏸"
        background = pill(Color.parseColor("#EE0A0E14"), Color.parseColor(if (paused) "#FFB020" else "#2BD67B"), 18f)
    }

    // Drag the panel by touching anywhere that isn't a button.
    override fun onInterceptTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> { downX = e.rawX; downY = e.rawY; dragging = false }
            MotionEvent.ACTION_MOVE -> if (!dragging && (kotlin.math.abs(e.rawX - downX) > slop || kotlin.math.abs(e.rawY - downY) > slop)) {
                dragging = true; return true
            }
        }
        return dragging
    }

    override fun onTouchEvent(e: MotionEvent): Boolean {
        when (e.actionMasked) {
            MotionEvent.ACTION_DOWN -> { downX = e.rawX; downY = e.rawY; return true }
            MotionEvent.ACTION_MOVE -> {
                onDrag((e.rawX - downX).toInt(), (e.rawY - downY).toInt()); downX = e.rawX; downY = e.rawY
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_CANCEL -> dragging = false
        }
        return true
    }
}
