import React, { useState } from 'react';
import { FlatList, Modal, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { Status } from '../native/AirCursor';
import { ACTIONS, GESTURES, GestureId, actionLabel } from '../settings';
import { useSettings } from '../hooks/useSettings';
import { colors, radius, space } from '../theme';
import { Button, Card, H1, H2, Muted } from '../components/ui';

export function GesturesScreen({ status }: { status: Status }) {
  const { settings, setGesture, resetGestures } = useSettings();
  const [picking, setPicking] = useState<GestureId | null>(null);
  const picked = GESTURES.find(g => g.id === picking);

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <H1>Gestures</H1>
      <Muted style={{ marginBottom: space.lg }}>
        Choose what each hand gesture does. The one you’re making lights up.
      </Muted>
      {GESTURES.map(g => (
        <Card key={g.id} active={status.running && !status.paused && status.hand && status.gesture === g.id}>
          <View style={styles.row}>
            <Text style={styles.emoji}>{g.emoji}</Text>
            <H2>{g.name}</H2>
          </View>
          <Muted>{g.how}</Muted>
          <Pressable style={styles.select} onPress={() => setPicking(g.id)} accessibilityRole="button"
            accessibilityLabel={`${g.name} action: ${actionLabel(settings.gestures[g.id])}`}>
            <Text style={styles.selectText}>{actionLabel(settings.gestures[g.id])}</Text>
            <Text style={styles.chev}>▾</Text>
          </Pressable>
        </Card>
      ))}
      <Button title="Reset gestures to defaults" onPress={resetGestures} />

      <Modal transparent visible={picking !== null} animationType="fade" onRequestClose={() => setPicking(null)}>
        <Pressable style={styles.backdrop} onPress={() => setPicking(null)}>
          <Pressable style={styles.sheet} onPress={() => undefined}>
            <H2>{picked ? `${picked.emoji}  ${picked.name} does…` : ''}</H2>
            <FlatList
              data={ACTIONS}
              keyExtractor={a => a.id}
              renderItem={({ item }) => {
                const on = picking && settings.gestures[picking] === item.id;
                return (
                  <Pressable style={[styles.opt, on && styles.optOn]}
                    onPress={() => { if (picking) { setGesture(picking, item.id); } setPicking(null); }}>
                    <Text style={[styles.optText, on && { color: colors.accent }]}>{item.label}</Text>
                    {on ? <Text style={{ color: colors.accent }}>✓</Text> : null}
                  </Pressable>
                );
              }}
            />
          </Pressable>
        </Pressable>
      </Modal>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: space.lg, paddingBottom: 40 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 4 },
  emoji: { fontSize: 26 },
  select: {
    marginTop: space.md, backgroundColor: colors.bg, borderColor: colors.border, borderWidth: 1,
    borderRadius: radius.sm, paddingVertical: 12, paddingHorizontal: 14,
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
  },
  selectText: { color: colors.text, fontSize: 14, fontWeight: '600' },
  chev: { color: colors.muted },
  backdrop: { flex: 1, backgroundColor: '#000A', justifyContent: 'flex-end' },
  sheet: {
    backgroundColor: colors.surface, borderTopLeftRadius: 22, borderTopRightRadius: 22,
    padding: space.lg, maxHeight: '75%', borderColor: colors.border, borderWidth: 1,
  },
  opt: { paddingVertical: 14, paddingHorizontal: 8, flexDirection: 'row', justifyContent: 'space-between', borderRadius: 10 },
  optOn: { backgroundColor: colors.surface2 },
  optText: { color: colors.text, fontSize: 15, fontWeight: '600' },
});
