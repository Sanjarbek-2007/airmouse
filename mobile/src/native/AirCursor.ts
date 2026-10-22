import { NativeEventEmitter, NativeModules, Platform } from 'react-native';

export type EngineState = {
  running: boolean;
  label: string;
  gesture: string;
  action: string;
  pending: string | null;
  progress: number;
  pinch: number;
  tuck: number;
  volume: number;
  factor: number;
  hand: boolean;
  paused: boolean;
  pauseReason: string;
  fps: number;
  error: string;
};

export type Status = EngineState & {
  accessibility: boolean;
  camera: boolean;
  notifications: boolean;
  sdk: number;
};

interface AirCursorNative {
  getStatus(): Promise<Status>;
  listCameras(): Promise<('front' | 'back')[]>;
  start(): Promise<boolean>;
  stop(): void;
  togglePause(): void;
  pause(): void;
  resume(): void;
  openAccessibilitySettings(): void;
  getSettings(): Promise<string>;
  saveSettings(json: string): Promise<boolean>;
  addListener(event: string): void;
  removeListeners(count: number): void;
}

const native: AirCursorNative | undefined =
  Platform.OS === 'android' ? (NativeModules.AirCursor as AirCursorNative | undefined) : undefined;

/** Idle state shown before the first update from native. */
export const IDLE_STATE: EngineState = {
  running: false, label: 'OFF', gesture: 'none', action: 'none', pending: null, progress: 0,
  pinch: 1, tuck: 1, volume: 0, factor: 1, hand: false, paused: false, pauseReason: '', fps: 0, error: '',
};

export const IDLE_STATUS: Status = {
  ...IDLE_STATE, accessibility: false, camera: false, notifications: true, sdk: 0,
};

const emitter = native ? new NativeEventEmitter(native as never) : undefined;

export const AirCursor = {
  available: !!native,
  getStatus: async (): Promise<Status> => (native ? native.getStatus() : IDLE_STATUS),
  listCameras: async (): Promise<('front' | 'back')[]> => (native ? native.listCameras() : ['front']),
  start: async (): Promise<void> => { if (native) { await native.start(); } },
  stop: () => native?.stop(),
  togglePause: () => native?.togglePause(),
  pause: () => native?.pause(),
  resume: () => native?.resume(),
  openAccessibilitySettings: () => native?.openAccessibilitySettings(),
  getSettingsJson: async (): Promise<string | null> => (native ? native.getSettings() : null),
  saveSettingsJson: async (json: string): Promise<void> => { if (native) { await native.saveSettings(json); } },
  /** Subscribe to live state (10 Hz while subscribed). Returns an unsubscribe function. */
  onState: (cb: (s: EngineState) => void): (() => void) => {
    if (!emitter) { return () => {}; }
    const sub = emitter.addListener('AirCursorState', (...args) => cb(args[0] as EngineState));
    return () => sub.remove();
  },
};
