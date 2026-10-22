import {
  ACTIONS, DEFAULT_GESTURES, DEFAULT_SETTINGS, GESTURES, SLIDERS, actionLabel, normalizeSettings,
} from '../src/settings';

describe('normalizeSettings', () => {
  it('returns defaults for garbage input', () => {
    expect(normalizeSettings(null)).toEqual(DEFAULT_SETTINGS);
    expect(normalizeSettings('nope')).toEqual(DEFAULT_SETTINGS);
    expect(normalizeSettings(42)).toEqual(DEFAULT_SETTINGS);
  });

  it('keeps valid values and ignores wrongly-typed ones', () => {
    const s = normalizeSettings({ speed: 2.2, smartMotion: false, smoothing: 'lots', mirror: 1 });
    expect(s.speed).toBe(2.2);
    expect(s.smartMotion).toBe(false);
    expect(s.smoothing).toBe(DEFAULT_SETTINGS.smoothing);
    expect(s.mirror).toBe(DEFAULT_SETTINGS.mirror);
  });

  it('merges gesture mappings and rejects unknown actions', () => {
    const s = normalizeSettings({ gestures: { fist: 'home', pinch: 'explode', bogus: 'tap' } });
    expect(s.gestures.fist).toBe('home');
    expect(s.gestures.pinch).toBe(DEFAULT_GESTURES.pinch);
    expect(Object.keys(s.gestures).sort()).toEqual(Object.keys(DEFAULT_GESTURES).sort());
  });

  it('falls back to the front camera for an invalid facing', () => {
    expect(normalizeSettings({ cameraFacing: 'sideways' }).cameraFacing).toBe('front');
    expect(normalizeSettings({ cameraFacing: 'back' }).cameraFacing).toBe('back');
  });

  it('does not mutate the shared defaults', () => {
    const s = normalizeSettings({ gestures: { fist: 'home' } });
    s.gestures.point = 'none';
    expect(DEFAULT_GESTURES.point).toBe('move');
    expect(DEFAULT_SETTINGS.gestures.fist).toBe('none');
  });
});

describe('metadata', () => {
  it('defines every gesture with a valid default action', () => {
    const actionIds = ACTIONS.map(a => a.id);
    GESTURES.forEach(g => expect(actionIds).toContain(DEFAULT_GESTURES[g.id]));
    expect(Object.keys(DEFAULT_GESTURES)).toHaveLength(GESTURES.length);
  });

  it('keeps every slider default inside its range', () => {
    Object.values(SLIDERS).flat().forEach(def => {
      const v = DEFAULT_SETTINGS[def.key];
      expect(v).toBeGreaterThanOrEqual(def.min);
      expect(v).toBeLessThanOrEqual(def.max);
    });
  });

  it('labels actions', () => {
    expect(actionLabel('tap')).toMatch(/tap/i);
    expect(actionLabel('mystery')).toBe('mystery');
  });
});
