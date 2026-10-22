package com.aircursor.rn

import com.facebook.react.BaseReactPackage
import com.facebook.react.bridge.NativeModule
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.module.model.ReactModuleInfo
import com.facebook.react.module.model.ReactModuleInfoProvider

class AirCursorPackage : BaseReactPackage() {
    override fun getModule(name: String, reactContext: ReactApplicationContext): NativeModule? =
        if (name == MODULE) AirCursorModule(reactContext) else null

    override fun getReactModuleInfoProvider() = ReactModuleInfoProvider {
        // (name, className, canOverrideExistingModule, needsEagerInit, isCxxModule, isTurboModule)
        mapOf(MODULE to ReactModuleInfo(MODULE, MODULE, false, false, false, false))
    }

    companion object { const val MODULE = "AirCursor" }
}
