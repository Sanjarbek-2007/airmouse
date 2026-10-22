import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AirCursor } from '../native/AirCursor';
import {
  ActionId, DEFAULT_GESTURES, DEFAULT_SETTINGS, GestureId, Settings, normalizeSettings,
} from '../settings';

type Ctx = {
  settings: Settings;
  loaded: boolean;
  update: (patch: Partial<Settings>) => void;
  setGesture: (g: GestureId, a: ActionId) => void;
  resetGestures: () => void;
  resetAll: () => void;
};

const SettingsContext = createContext<Ctx | null>(null);

/** Loads settings from native storage and saves changes back (debounced). The running
 *  service reads the same live settings object, so changes apply instantly. */
export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [loaded, setLoaded] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let alive = true;
    AirCursor.getSettingsJson()
      .then(json => { if (alive) { setSettings(normalizeSettings(json ? JSON.parse(json) : null)); } })
      .catch(() => {})
      .finally(() => { if (alive) { setLoaded(true); } });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!loaded) { return; }
    if (timer.current) { clearTimeout(timer.current); }
    timer.current = setTimeout(() => { AirCursor.saveSettingsJson(JSON.stringify(settings)).catch(() => {}); }, 250);
    return () => { if (timer.current) { clearTimeout(timer.current); } };
  }, [settings, loaded]);

  const update = useCallback((patch: Partial<Settings>) => setSettings(s => ({ ...s, ...patch })), []);
  const setGesture = useCallback((g: GestureId, a: ActionId) =>
    setSettings(s => ({ ...s, gestures: { ...s.gestures, [g]: a } })), []);
  const resetGestures = useCallback(() =>
    setSettings(s => ({ ...s, gestures: { ...DEFAULT_GESTURES } })), []);
  const resetAll = useCallback(() =>
    setSettings(s => ({ ...DEFAULT_SETTINGS, cameraFacing: s.cameraFacing, gestures: { ...DEFAULT_GESTURES } })), []);

  const value = useMemo(
    () => ({ settings, loaded, update, setGesture, resetGestures, resetAll }),
    [settings, loaded, update, setGesture, resetGestures, resetAll],
  );
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}

export function useSettings(): Ctx {
  const ctx = useContext(SettingsContext);
  if (!ctx) { throw new Error('useSettings must be used inside <SettingsProvider>'); }
  return ctx;
}
