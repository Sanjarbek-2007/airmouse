package com.aircursor.service

import com.aircursor.engine.EngineView

/** Latest engine state, written by the camera service and read by the UI bridge. */
object EngineBus {
    @Volatile var view: EngineView = EngineView()
    @Volatile var fps: Double = 0.0
    @Volatile var error: String = ""
}
