import React from 'react';

jest.mock('react-native-safe-area-context', () =>
  require('react-native-safe-area-context/jest/mock').default);

import ReactTestRenderer from 'react-test-renderer';
import App from '../App';
import { HomeScreen } from '../src/screens/HomeScreen';
import { GesturesScreen } from '../src/screens/GesturesScreen';
import { SettingsProvider } from '../src/hooks/useSettings';
import { IDLE_STATUS, Status } from '../src/native/AirCursor';

const texts = (r: ReactTestRenderer.ReactTestRenderer): string =>
  JSON.stringify(r.toJSON());

const mounted: ReactTestRenderer.ReactTestRenderer[] = [];

const render = async (el: React.ReactElement) => {
  let r!: ReactTestRenderer.ReactTestRenderer;
  await ReactTestRenderer.act(async () => { r = ReactTestRenderer.create(el); });
  mounted.push(r);
  return r;
};

afterEach(async () => {
  // unmount so the polling timers / listeners in the hooks are cleared
  await ReactTestRenderer.act(async () => { mounted.splice(0).forEach(r => r.unmount()); });
});

test('app renders with all four tabs', async () => {
  const r = await render(<App />);
  const t = texts(r);
  ['Home', 'Gestures', 'Settings', 'Guide'].forEach(label => expect(t).toContain(label));
  expect(t).toContain('Start hand control');
});

test('home shows the setup checklist until permissions are granted', async () => {
  const r = await render(<HomeScreen status={IDLE_STATUS} refresh={() => {}} />);
  const t = texts(r);
  expect(t).toContain('Accessibility service');
  expect(t).toContain('Camera');
});

test('home shows live command and pause/stop controls while running', async () => {
  const status: Status = {
    ...IDLE_STATUS, running: true, camera: true, accessibility: true, hand: true,
    label: 'TAP', gesture: 'pinch', action: 'tap',
  };
  const r = await render(<HomeScreen status={status} refresh={() => {}} />);
  const t = texts(r);
  expect(t).toContain('TAP');
  expect(t).toContain('Pause');
  expect(t).toContain('Stop');
  expect(t).not.toContain('Start hand control');
});

test('home shows the resume button and reason when paused', async () => {
  const status: Status = {
    ...IDLE_STATUS, running: true, camera: true, accessibility: true,
    paused: true, label: 'PAUSED', pauseReason: 'Safety guard: 6 presses in 2s',
  };
  const t = texts(await render(<HomeScreen status={status} refresh={() => {}} />));
  expect(t).toContain('Resume');
  expect(t).toContain('Safety guard');
});

test('gestures screen lists every gesture with its default action', async () => {
  const r = await render(
    <SettingsProvider><GesturesScreen status={IDLE_STATUS} /></SettingsProvider>,
  );
  const t = texts(r);
  ['Point', 'Pinch', 'Thumb tuck', 'Peace', 'Fist', 'Open palm'].forEach(n => expect(t).toContain(n));
  expect(t).toContain('Tap / touch & drag');
  expect(t).toContain('Volume dial');
});
