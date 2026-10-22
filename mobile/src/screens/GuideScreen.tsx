import React from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import { GESTURES, actionLabel, DEFAULT_GESTURES } from '../settings';
import { colors, space } from '../theme';
import { Card, H1, H2, Muted } from '../components/ui';

const Step = ({ n, text }: { n: number; text: string }) => (
  <View style={styles.step}>
    <Text style={styles.n}>{n}</Text>
    <Text style={styles.stepText}>{text}</Text>
  </View>
);

export function GuideScreen() {
  return (
    <ScrollView contentContainerStyle={styles.page}>
      <H1>Guide</H1>
      <Muted style={{ marginBottom: space.lg }}>Everything you need in one minute.</Muted>

      <Card>
        <H2>Quick start</H2>
        <Step n={1} text="Allow the camera, then switch on the AirCursor accessibility service (Home → Setup)." />
        <Step n={2} text="Prop your phone up (or hold it in one hand) so the front camera sees your other hand." />
        <Step n={3} text="Tap Start hand control. Raise your index finger and move: the cursor moves like a mouse." />
        <Step n={4} text="Pinch thumb and index finger to tap. Hold the pinch and move to drag." />
        <Muted style={{ marginTop: space.md }}>
          Run out of room? Open your palm to lift the “mouse”, move your hand back, and point again. Want faster
          corner reach? Raise Long-reach boost in Settings (off by default).
        </Muted>
      </Card>

      <Card>
        <H2>Default gestures</H2>
        {GESTURES.map(g => (
          <View key={g.id} style={styles.gRow}>
            <Text style={styles.emoji}>{g.emoji}</Text>
            <View style={styles.flex}>
              <Text style={styles.gName}>{g.name} <Text style={{ color: colors.accent }}>→ {actionLabel(DEFAULT_GESTURES[g.id])}</Text></Text>
              <Muted>{g.how}</Muted>
            </View>
          </View>
        ))}
      </Card>

      <Card>
        <H2>Why it won’t misfire</H2>
        <Muted>• A gesture must be held steadily for a split second before it counts.</Muted>
        <Muted>• While a new gesture is being recognised, the cursor holds still, so taps land where you aimed.</Muted>
        <Muted>• A fist never taps.</Muted>
        <Muted>• A burst of taps triggers the safety guard, which pauses everything.</Muted>
      </Card>

      <Card>
        <H2>Stopping it fast</H2>
        <Muted>• The floating ⏸ / ✕ panel stays on top of every app.</Muted>
        <Muted>• Volume Up + Volume Down together: pause / resume.</Muted>
        <Muted>• Pause and Stop buttons in the notification.</Muted>
        <Muted>• Turn off the accessibility service in Android settings to remove all control.</Muted>
      </Card>

      <Card>
        <H2>Troubleshooting</H2>
        <Muted>• Hand not detected: more light, hand fully in view, plain background.</Muted>
        <Muted>• Taps too hard or easy: change Pinch sensitivity in Settings.</Muted>
        <Muted>• Android blocks the accessibility service: App info → ⋮ → Allow restricted settings.</Muted>
        <Muted>• Video never leaves your phone; nothing is uploaded.</Muted>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: space.lg, paddingBottom: 40 },
  step: { flexDirection: 'row', gap: 12, marginTop: space.md, alignItems: 'flex-start' },
  n: {
    color: '#04121A', backgroundColor: colors.accent, width: 24, height: 24, borderRadius: 12,
    textAlign: 'center', fontWeight: '800', lineHeight: 24, overflow: 'hidden',
  },
  stepText: { color: colors.text, flex: 1, fontSize: 14, lineHeight: 20 },
  gRow: { flexDirection: 'row', gap: 12, marginTop: space.md },
  emoji: { fontSize: 26, width: 34 },
  flex: { flex: 1 },
  gName: { color: colors.text, fontWeight: '700', fontSize: 14 },
});
