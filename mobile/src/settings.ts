/** Settings model shared with the native side (JSON). Keep in sync with SettingsStore.kt. */

export type GestureId =
  | 'point' | 'pinch' | 'tuck' | 'peace' | 'three' | 'rock' | 'fist' | 'open';

export type ActionId =
  | 'none' | 'move' | 'tap' | 'back' | 'home' | 'recents' | 'notifications'
  | 'scroll' | 'fast_scroll' | 'volume';

export type Settings = {
  speed: number;
  smartMotion: boolean;
  accelStrength: number;
  longMoveBoost: number;
  smoothing: number;
  holdScale: number;
  pinchSensitivity: number;
  tuckSensitivity: number;
  scrollSpeed: number;
  volumeStep: number;
  guardEnabled: boolean;
  guardClicks: number;
  guardWindow: number;
  mirror: boolean;
  cameraFacing: 'front' | 'back';
  showCursor: boolean;
  cursorSize: number;
  floatPanel: boolean;
  gestures: Record<GestureId, ActionId>;
};

export const DEFAULT_GESTURES: Record<GestureId, ActionId> = {
  point: 'move',
  pinch: 'tap',
  tuck: 'back',
  peace: 'scroll',
  three: 'fast_scroll',
  rock: 'volume',
  fist: 'none',
  open: 'none',
};

export const DEFAULT_SETTINGS: Settings = {
  speed: 1.0,
  smartMotion: true,
  accelStrength: 0.0,
  longMoveBoost: 0.0,
  smoothing: 0.5,
  holdScale: 1.0,
  pinchSensitivity: 1.0,
  tuckSensitivity: 1.0,
  scrollSpeed: 1.0,
  volumeStep: 10,
  guardEnabled: true,
  guardClicks: 6,
  guardWindow: 2.0,
  mirror: true,
  cameraFacing: 'front',
  showCursor: true,
  cursorSize: 22,
  floatPanel: true,
  gestures: { ...DEFAULT_GESTURES },
};

export type SliderKey =
  | 'speed' | 'accelStrength' | 'longMoveBoost' | 'smoothing' | 'holdScale'
  | 'pinchSensitivity' | 'tuckSensitivity' | 'scrollSpeed' | 'volumeStep' | 'cursorSize';

export type SliderDef = {
  key: SliderKey;
  label: string;
  help: string;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
};

const x2 = (v: number) => `${v.toFixed(2)}×`;
const x1 = (v: number) => `${v.toFixed(1)}×`;

export const SLIDERS: Record<string, SliderDef[]> = {
  Pointer: [
    { key: 'speed', label: 'Pointer speed', min: 0.3, max: 3, step: 0.05, format: x2,
      help: 'How far the cursor travels for a given hand movement. Hand-size aware, so it feels the same near or far.' },
    { key: 'accelStrength', label: 'Speed-up on fast moves', min: 0, max: 2, step: 0.05,
      format: v => v.toFixed(2),
      help: 'Optional. Move fast and the cursor travels extra far. 0 = off: the cursor follows your hand 1:1.' },
    { key: 'longMoveBoost', label: 'Long-reach boost', min: 0, max: 2, step: 0.05,
      format: v => v.toFixed(2),
      help: 'Optional. Keep moving one way and the cursor gets faster, for reaching corners. 0 = off.' },
    { key: 'smoothing', label: 'Smoothing', min: 0, max: 1, step: 0.05,
      format: v => `${Math.round(v * 100)}%`,
      help: 'Higher = steadier cursor with slightly more lag.' },
  ],
  Recognition: [
    { key: 'holdScale', label: 'Gesture confirmation time', min: 0.5, max: 2.5, step: 0.1, format: x1,
      help: 'How long a gesture must be held steadily before it counts. Raise it if you get accidental actions.' },
    { key: 'pinchSensitivity', label: 'Pinch sensitivity', min: 0.6, max: 1.5, step: 0.05,
      format: v => v.toFixed(2), help: 'Higher = a looser pinch counts as a tap.' },
    { key: 'tuckSensitivity', label: 'Thumb-tuck sensitivity', min: 0.6, max: 1.5, step: 0.05,
      format: v => v.toFixed(2), help: 'Higher = the thumb doesn’t have to tuck as far.' },
  ],
  Actions: [
    { key: 'scrollSpeed', label: 'Scroll speed', min: 0.3, max: 3, step: 0.1, format: x1,
      help: 'How far a slide gesture scrolls.' },
    { key: 'volumeStep', label: 'Volume per circle', min: 5, max: 25, step: 1,
      format: v => `${Math.round(v)}%`, help: 'Volume change for one full finger circle.' },
  ],
  Cursor: [
    { key: 'cursorSize', label: 'Cursor size', min: 12, max: 48, step: 2,
      format: v => `${Math.round(v)} dp`, help: 'Size of the on-screen cursor ring.' },
  ],
};

export type ToggleKey = 'smartMotion' | 'mirror' | 'showCursor' | 'floatPanel' | 'guardEnabled';

export const TOGGLES: { key: ToggleKey; label: string; help: string }[] = [
  { key: 'smartMotion', label: 'Smart motion', help: 'Master switch for the two optional boosts above (both 0 = off by default).' },
  { key: 'mirror', label: 'Mirror camera', help: 'Move your hand right and the cursor moves right (like a mirror).' },
  { key: 'showCursor', label: 'Show cursor', help: 'Draw the on-screen cursor ring.' },
  { key: 'floatPanel', label: 'Floating pause / stop panel', help: 'Always-on-top panel with Pause and Stop.' },
  { key: 'guardEnabled', label: 'Safety guard', help: 'Auto-pause if many taps happen in a few seconds.' },
];

export const GESTURES: { id: GestureId; emoji: string; name: string; how: string }[] = [
  { id: 'point', emoji: '☝️', name: 'Point', how: 'Raise only your index finger. Move your hand to move the cursor.' },
  { id: 'pinch', emoji: '🤏', name: 'Pinch', how: 'Touch thumb tip to index tip, other fingers open. Quick = tap, hold and move = drag.' },
  { id: 'tuck', emoji: '🖐️', name: 'Thumb tuck', how: 'Open hand, then fold your thumb into your palm (the “signal for help” pose).' },
  { id: 'peace', emoji: '✌️', name: 'Peace', how: 'Index and middle finger up, ring and pinky down.' },
  { id: 'three', emoji: '🤟', name: 'Three fingers', how: 'Index, middle and ring finger up, pinky down.' },
  { id: 'rock', emoji: '🤘', name: 'Rock sign', how: 'Index and pinky up, middle and ring down.' },
  { id: 'fist', emoji: '✊', name: 'Fist', how: 'Close your whole hand. A fist never taps.' },
  { id: 'open', emoji: '✋', name: 'Open palm', how: 'All fingers open. The resting pose: lifts the “mouse”.' },
];

export const ACTIONS: { id: ActionId; label: string }[] = [
  { id: 'none', label: 'Do nothing' },
  { id: 'move', label: 'Move cursor' },
  { id: 'tap', label: 'Tap / touch & drag' },
  { id: 'back', label: 'Back' },
  { id: 'home', label: 'Home' },
  { id: 'recents', label: 'Recent apps' },
  { id: 'notifications', label: 'Notifications' },
  { id: 'scroll', label: 'Scroll (move hand)' },
  { id: 'fast_scroll', label: 'Fast scroll (3×)' },
  { id: 'volume', label: 'Volume dial (circle fingertip)' },
];

export const actionLabel = (id: string) => ACTIONS.find(a => a.id === id)?.label ?? id;
export const gestureInfo = (id: string) => GESTURES.find(g => g.id === id);

/** Merge unknown JSON from native into a complete, valid Settings object. */
export function normalizeSettings(raw: unknown): Settings {
  const out: Settings = { ...DEFAULT_SETTINGS, gestures: { ...DEFAULT_GESTURES } };
  if (!raw || typeof raw !== 'object') { return out; }
  const r = raw as Record<string, unknown>;
  (Object.keys(DEFAULT_SETTINGS) as (keyof Settings)[]).forEach(k => {
    if (k === 'gestures') { return; }
    const v = r[k];
    if (typeof v === typeof DEFAULT_SETTINGS[k]) { (out as Record<string, unknown>)[k] = v; }
  });
  if (out.cameraFacing !== 'front' && out.cameraFacing !== 'back') { out.cameraFacing = 'front'; }
  const g = r.gestures as Record<string, string> | undefined;
  if (g && typeof g === 'object') {
    (Object.keys(DEFAULT_GESTURES) as GestureId[]).forEach(id => {
      if (ACTIONS.some(a => a.id === g[id])) { out.gestures[id] = g[id] as ActionId; }
    });
  }
  return out;
}
