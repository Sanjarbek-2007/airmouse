package com.aircursor.rn

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.hardware.camera2.CameraCharacteristics
import android.hardware.camera2.CameraManager
import android.os.Build
import android.os.Handler
import android.os.Looper
import android.provider.Settings
import com.aircursor.service.AirAccessibilityService
import com.aircursor.service.AirCursorService
import com.aircursor.service.EngineBus
import com.aircursor.service.SettingsStore
import com.facebook.react.bridge.Arguments
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod
import com.facebook.react.bridge.WritableMap
import com.facebook.react.modules.core.DeviceEventManagerModule

/**
 * JS <-> native bridge. JS drives start/stop/pause and settings; native pushes live state
 * back as "AirCursorState" events (10 Hz, only while JS is listening).
 */
class AirCursorModule(private val rc: ReactApplicationContext) : ReactContextBaseJavaModule(rc) {
    private val main = Handler(Looper.getMainLooper())
    private var listeners = 0
    private val ticker = object : Runnable {
        override fun run() {
            if (listeners > 0) {
                rc.getJSModule(DeviceEventManagerModule.RCTDeviceEventEmitter::class.java).emit("AirCursorState", stateMap())
                main.postDelayed(this, 100)
            }
        }
    }

    override fun getName() = "AirCursor"

    private fun stateMap(): WritableMap {
        val v = EngineBus.view
        return Arguments.createMap().apply {
            putBoolean("running", AirCursorService.instance != null)
            putString("label", v.label)
            putString("gesture", v.gesture)
            putString("action", v.action)
            putString("pending", v.pending)
            putDouble("progress", v.progress)
            putDouble("pinch", v.pinch)
            putDouble("tuck", v.tuck)
            putDouble("volume", v.volume)
            putDouble("factor", v.factor)
            putBoolean("hand", v.hand)
            putBoolean("paused", v.paused)
            putString("pauseReason", v.pauseReason)
            putDouble("fps", EngineBus.fps)
            putString("error", EngineBus.error)
        }
    }

    private fun accessibilityEnabled(): Boolean {
        if (AirAccessibilityService.instance != null) return true
        val enabled = Settings.Secure.getString(rc.contentResolver, Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES) ?: return false
        return enabled.split(':').any { it.startsWith("${rc.packageName}/") && it.contains("AirAccessibilityService") }
    }

    // ----------------------------------------------------------------- status
    @ReactMethod
    fun getStatus(promise: Promise) {
        promise.resolve(stateMap().apply {
            putBoolean("accessibility", accessibilityEnabled())
            putBoolean("camera", rc.checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED)
            putBoolean("notifications", Build.VERSION.SDK_INT < 33 ||
                rc.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED)
            putInt("sdk", Build.VERSION.SDK_INT)
        })
    }

    @ReactMethod
    fun listCameras(promise: Promise) {
        try {
            val mgr = rc.getSystemService(CameraManager::class.java)
            val facings = mgr.cameraIdList.mapNotNull { mgr.getCameraCharacteristics(it).get(CameraCharacteristics.LENS_FACING) }.toSet()
            val arr = Arguments.createArray()
            if (CameraCharacteristics.LENS_FACING_FRONT in facings) arr.pushString("front")
            if (CameraCharacteristics.LENS_FACING_BACK in facings) arr.pushString("back")
            promise.resolve(arr)
        } catch (e: Exception) {
            promise.reject("camera", e.message, e)
        }
    }

    // ---------------------------------------------------------------- control
    @ReactMethod fun start(promise: Promise) {
        when {
            !accessibilityEnabled() -> promise.reject("accessibility", "Turn on the AirCursor accessibility service first.")
            rc.checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED ->
                promise.reject("camera", "Camera permission is needed.")
            else -> { SettingsStore.ensureLoaded(rc); AirCursorService.start(rc); promise.resolve(true) }
        }
    }

    @ReactMethod fun stop() { AirCursorService.stop(rc) }
    @ReactMethod fun togglePause() { AirCursorService.togglePause() }
    @ReactMethod fun pause() { AirCursorService.pause() }
    @ReactMethod fun resume() { AirCursorService.resume() }

    @ReactMethod fun openAccessibilitySettings() {
        rc.startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    }

    // --------------------------------------------------------------- settings
    @ReactMethod fun getSettings(promise: Promise) {
        SettingsStore.ensureLoaded(rc)
        promise.resolve(SettingsStore.toJson())
    }

    @ReactMethod fun saveSettings(json: String, promise: Promise) {
        try {
            SettingsStore.save(rc, json)
            AirAccessibilityService.instance?.applySettings()
            AirCursorService.instance?.onSettingsChanged()
            promise.resolve(true)
        } catch (e: Exception) {
            promise.reject("settings", e.message, e)
        }
    }

    // ----------------------------------------------------------------- events
    @ReactMethod fun addListener(eventName: String) {
        if (listeners++ == 0) main.post(ticker)
    }

    @ReactMethod fun removeListeners(count: Double) {
        listeners = (listeners - count.toInt()).coerceAtLeast(0)
    }
}
