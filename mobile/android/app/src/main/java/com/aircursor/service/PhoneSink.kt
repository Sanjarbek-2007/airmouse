package com.aircursor.service

import android.content.Context
import android.media.AudioManager
import com.aircursor.engine.ActionSink
import com.aircursor.engine.GlobalAction

/** Connects the engine to the phone: the accessibility service for touch/cursor/global actions,
 *  the audio manager for volume. If the accessibility service isn't connected, actions are dropped. */
class PhoneSink(ctx: Context) : ActionSink {
    private val audio = ctx.applicationContext.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    private val svc get() = AirAccessibilityService.instance

    override fun moveBy(dx: Float, dy: Float) { svc?.moveCursorBy(dx, dy) }
    override fun pressDown() { svc?.touchDown() }
    override fun pressUp() { svc?.touchUp() }
    override fun scroll(dx: Int, dy: Int) { svc?.scrollBy(dx, dy) }
    override fun global(action: GlobalAction) { svc?.performGlobal(action) }
    override fun cancelMotion() { svc?.cancelMotion() }

    override fun volumeGet(): Float {
        val max = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC).coerceAtLeast(1)
        return audio.getStreamVolume(AudioManager.STREAM_MUSIC).toFloat() / max
    }

    override fun volumeSet(v: Float) {
        val max = audio.getStreamMaxVolume(AudioManager.STREAM_MUSIC)
        audio.setStreamVolume(AudioManager.STREAM_MUSIC, Math.round(v.coerceIn(0f, 1f) * max), AudioManager.FLAG_SHOW_UI)
    }
}
