package com.aircursor.service

import android.content.Context
import com.aircursor.engine.Action
import com.aircursor.engine.DEFAULT_MAPPING
import com.aircursor.engine.EngineSettings
import com.aircursor.engine.Gesture
import org.json.JSONObject

/** App-level settings that are not part of the gesture engine. */
class AppExtras {
    @Volatile var mirror = true
    @Volatile var cameraFacing = "front"      // "front" | "back"
    @Volatile var showCursor = true
    @Volatile var cursorSize = 22.0           // dp
    @Volatile var floatPanel = true
}

/**
 * Single source of truth, shared by the React Native UI (which writes JSON) and the services
 * (which read the live objects every frame, so changes apply instantly).
 */
object SettingsStore {
    val engine = EngineSettings()
    val extras = AppExtras()
    private const val PREFS = "aircursor"
    private const val KEY = "settings_json"

    @Volatile private var loaded = false

    fun ensureLoaded(ctx: Context) {
        if (loaded) return
        synchronized(this) {
            if (loaded) return
            ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).getString(KEY, null)?.let { runCatching { apply(it) } }
            loaded = true
        }
    }

    /** Parse JSON from the UI into the live settings objects. Unknown / invalid keys are ignored. */
    fun apply(json: String) {
        val o = JSONObject(json)
        val e = engine
        e.speed = o.optDouble("speed", e.speed).coerceIn(0.3, 3.0)
        e.smartMotion = o.optBoolean("smartMotion", e.smartMotion)
        e.accelStrength = o.optDouble("accelStrength", e.accelStrength).coerceIn(0.0, 2.0)
        e.longMoveBoost = o.optDouble("longMoveBoost", e.longMoveBoost).coerceIn(0.0, 2.0)
        e.smoothing = o.optDouble("smoothing", e.smoothing).coerceIn(0.0, 1.0)
        e.holdScale = o.optDouble("holdScale", e.holdScale).coerceIn(0.5, 2.5)
        e.pinchSensitivity = o.optDouble("pinchSensitivity", e.pinchSensitivity).coerceIn(0.6, 1.5)
        e.tuckSensitivity = o.optDouble("tuckSensitivity", e.tuckSensitivity).coerceIn(0.6, 1.5)
        e.scrollSpeed = o.optDouble("scrollSpeed", e.scrollSpeed).coerceIn(0.3, 3.0)
        e.volumeStep = o.optDouble("volumeStep", e.volumeStep).coerceIn(5.0, 25.0)
        e.guardEnabled = o.optBoolean("guardEnabled", e.guardEnabled)
        e.guardClicks = o.optInt("guardClicks", e.guardClicks).coerceIn(3, 30)
        e.guardWindow = o.optDouble("guardWindow", e.guardWindow).coerceIn(1.0, 10.0)
        o.optJSONObject("gestures")?.let { g ->
            val map = DEFAULT_MAPPING.toMutableMap()
            for (gesture in Gesture.values()) {
                if (gesture == Gesture.NONE) continue
                val action = Action.fromId(g.optString(gesture.id, ""))
                if (action != null) map[gesture] = action
            }
            e.gestures = map
        }
        val x = extras
        x.mirror = o.optBoolean("mirror", x.mirror)
        x.cameraFacing = o.optString("cameraFacing", x.cameraFacing).let { if (it == "back") "back" else "front" }
        x.showCursor = o.optBoolean("showCursor", x.showCursor)
        x.cursorSize = o.optDouble("cursorSize", x.cursorSize).coerceIn(12.0, 48.0)
        x.floatPanel = o.optBoolean("floatPanel", x.floatPanel)
    }

    fun toJson(): String {
        val e = engine
        val g = JSONObject()
        for ((gesture, action) in e.gestures) g.put(gesture.id, action.id)
        return JSONObject()
            .put("speed", e.speed).put("smartMotion", e.smartMotion).put("accelStrength", e.accelStrength)
            .put("longMoveBoost", e.longMoveBoost).put("smoothing", e.smoothing).put("holdScale", e.holdScale)
            .put("pinchSensitivity", e.pinchSensitivity).put("tuckSensitivity", e.tuckSensitivity)
            .put("scrollSpeed", e.scrollSpeed).put("volumeStep", e.volumeStep)
            .put("guardEnabled", e.guardEnabled).put("guardClicks", e.guardClicks).put("guardWindow", e.guardWindow)
            .put("mirror", extras.mirror).put("cameraFacing", extras.cameraFacing)
            .put("showCursor", extras.showCursor).put("cursorSize", extras.cursorSize)
            .put("floatPanel", extras.floatPanel).put("gestures", g)
            .toString()
    }

    fun save(ctx: Context, json: String) {
        apply(json)
        ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().putString(KEY, toJson()).apply()
    }
}
