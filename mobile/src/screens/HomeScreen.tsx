import React, { useState } from 'react';
import { Alert, ScrollView, StyleSheet, Text, View } from 'react-native';
import { AirCursor, Status } from '../native/AirCursor';
import { requestCamera, requestNotifications } from '../permissions';
import { actionLabel, gestureInfo } from '../settings';
import { colors, space } from '../theme';
import { Button, Card, H1, H2, Meter, Muted, Pill } from '../components/ui';

function Step({ done, title, detail, action, onPress }: {
  done: boolean; title: string; detail: string; action: string; onPress: () => void;
}) {
  return (
    <View style={styles.step}>
      <Text style={[styles.tick, { color: done ? colors.green : colors.amber }]}>{done ? '✓' : '•'}</Text>
      <View style={styles.flex}>
        <H2>{title}</H2>
        <Muted>{detail}</Muted>
      </View>
      {!done && <Button title={action} onPress={onPress} kind="primary" style={styles.stepBtn} />}
    </View>
  );
}

export function HomeScreen({ status, refresh }: { status: Status; refresh: () => void }) {
  const [busy, setBusy] = useState(false);
  const ready = status.camera && status.accessibility;
  const info = gestureInfo(status.gesture);

  const start = async () => {
    setBusy(true);
    try { await AirCursor.start(); } catch (e) {
      Alert.alert('Cannot start', (e as Error).message);
    } finally { setBusy(false); refresh(); }
  };

  const pill = !status.running ? <Pill text="OFF" />
    : status.paused ? <Pill text="PAUSED" kind="warn" /> : <Pill text="ACTIVE" kind="ok" />;

  const pending = status.pending && status.pending !== 'none' ? gestureInfo(status.pending) : undefined;

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.head}>
        <View style={styles.flex}>
          <H1>AirCursor</H1>
          <Muted>Control your phone with your hand.</Muted>
        </View>
        {pill}
      </View>

      {status.error ? (
        <Card style={styles.errCard}><Text style={styles.errText}>⚠  {status.error}</Text></Card>
      ) : null}

      <Card active={status.running && !status.paused && status.hand}>
        <View style={styles.cmdRow}>
          <Text style={styles.emoji}>{status.running ? (info?.emoji ?? '👋') : '✋'}</Text>
          <Text style={[styles.cmd, status.paused && { color: colors.amber }]} numberOfLines={1} adjustsFontSizeToFit>
            {status.running ? status.label : 'Not running'}
          </Text>
        </View>
        <Muted>
          {!status.running ? 'Start hand control, then hold your hand in front of the camera.'
            : status.paused ? (status.pauseReason || 'Paused — nothing you do will act.')
            : info ? `${info.name}  →  ${actionLabel(status.action)}` : 'Show your hand to the camera'}
        </Muted>
        {status.running && (
          <>
            <Meter label={pending ? `Recognising ${pending.name}…` : 'Recognised'}
              value={pending ? status.progress : status.hand ? 1 : 0}
              kind={pending ? 'warn' : status.hand ? 'ok' : undefined} />
            <Meter label="Pinch" value={(0.8 - status.pinch) / 0.5} kind={status.gesture === 'pinch' ? 'ok' : undefined}
              text={status.hand ? status.pinch.toFixed(2) : ''} />
            <Meter label="Thumb tuck" value={(1 - status.tuck) / 0.5} kind={status.gesture === 'tuck' ? 'ok' : undefined}
              text={status.hand ? status.tuck.toFixed(2) : ''} />
            {status.action === 'volume' && <Meter label="Volume" value={status.volume} text={`${Math.round(status.volume * 100)}%`} />}
            {status.factor > 1.08 && <Meter label="Reach boost" value={(status.factor - 1) / 3} kind="warn" text={`×${status.factor.toFixed(1)}`} />}
          </>
        )}
      </Card>

      {status.running ? (
        <View style={styles.buttons}>
          <Button kind={status.paused ? 'success' : 'warn'} style={styles.flex}
            title={status.paused ? '▶  Resume' : '⏸  Pause'} onPress={() => AirCursor.togglePause()} />
          <Button kind="danger" style={styles.flex} title="✕  Stop" onPress={() => AirCursor.stop()} />
        </View>
      ) : (
        <Button kind="primary" title={busy ? 'Starting…' : 'Start hand control'} disabled={!ready || busy} onPress={start} />
      )}

      {(!ready || !status.notifications) && !status.running && (
        <Card style={{ marginTop: space.lg }}>
          <H2>Setup</H2>
          <Step done={status.camera} title="Camera" detail="Needed to see your hand. Video stays on your phone."
            action="Allow" onPress={async () => { await requestCamera(); refresh(); }} />
          <Step done={status.accessibility} title="Accessibility service"
            detail="Lets AirCursor draw the cursor and tap, drag and scroll for you. Find “AirCursor” in the list and turn it on. (If Android says it’s restricted: App info → ⋮ → Allow restricted settings.)"
            action="Open" onPress={() => AirCursor.openAccessibilitySettings()} />
          <Step done={status.notifications} title="Notifications"
            detail="Shows the Pause / Stop buttons while AirCursor is running." action="Allow"
            onPress={async () => { await requestNotifications(); refresh(); }} />
        </Card>
      )}

      <Card style={{ marginTop: space.lg }}>
        <H2>Stop it any time</H2>
        <Muted>• Floating ⏸ / ✕ panel stays on top of every app.</Muted>
        <Muted>• Press Volume Up and Volume Down together to pause or resume.</Muted>
        <Muted>• The notification has Pause and Stop buttons.</Muted>
        <Muted>• Touching the screen normally always works.</Muted>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  page: { padding: space.lg, paddingBottom: 40 },
  head: { flexDirection: 'row', alignItems: 'center', marginBottom: space.lg },
  cmdRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 4 },
  emoji: { fontSize: 34 },
  cmd: { color: colors.text, fontSize: 30, fontWeight: '800', flex: 1 },
  buttons: { flexDirection: 'row', gap: 12 },
  step: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: space.md },
  tick: { fontSize: 22, fontWeight: '900', width: 22, textAlign: 'center' },
  stepBtn: { paddingVertical: 8, paddingHorizontal: 14 },
  errCard: { borderColor: colors.red, backgroundColor: '#2B1217' },
  errText: { color: colors.red, fontWeight: '600' },
});
