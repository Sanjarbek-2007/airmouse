import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { AirCursor } from '../native/AirCursor';
import { SLIDERS, TOGGLES } from '../settings';
import { useSettings } from '../hooks/useSettings';
import { colors, radius, space } from '../theme';
import { Button, Card, H1, H2, Muted, SliderRow, ToggleRow } from '../components/ui';

function Segmented<T extends string>({ value, options, onChange }: {
  value: T; options: { id: T; label: string }[]; onChange: (v: T) => void;
}) {
  return (
    <View style={styles.seg}>
      {options.map(o => (
        <Pressable key={o.id} style={[styles.segItem, value === o.id && styles.segOn]} onPress={() => onChange(o.id)}
          accessibilityRole="button" accessibilityState={{ selected: value === o.id }}>
          <Text style={[styles.segText, value === o.id && styles.segTextOn]}>{o.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

export function SettingsScreen() {
  const { settings, update, resetAll } = useSettings();
  const [cams, setCams] = useState<('front' | 'back')[]>(['front', 'back']);
  useEffect(() => { AirCursor.listCameras().then(setCams).catch(() => {}); }, []);

  const sections = [
    { title: 'Pointer', toggles: ['smartMotion' as const] },
    { title: 'Recognition', toggles: [] as never[] },
    { title: 'Actions', toggles: [] as never[] },
    { title: 'Cursor', toggles: ['showCursor' as const, 'floatPanel' as const] },
  ];

  return (
    <ScrollView contentContainerStyle={styles.page}>
      <View style={styles.head}>
        <View style={styles.flex}><H1>Settings</H1><Muted>Applied instantly, saved automatically.</Muted></View>
        <Button title="Reset" onPress={resetAll} style={styles.resetBtn} />
      </View>

      {sections.map(sec => (
        <Card key={sec.title}>
          <H2>{sec.title}</H2>
          {(SLIDERS[sec.title] ?? []).map(def => (
            <SliderRow key={def.key} def={def} value={settings[def.key]} onChange={v => update({ [def.key]: v })} />
          ))}
          {sec.toggles.map(k => {
            const t = TOGGLES.find(x => x.key === k)!;
            return <ToggleRow key={k} label={t.label} help={t.help} value={settings[k]} onChange={v => update({ [k]: v })} />;
          })}
        </Card>
      ))}

      <Card>
        <H2>Camera</H2>
        <Muted>Which camera watches your hand. Prop the phone up, or hold it in one hand and use the other.</Muted>
        <View style={{ height: space.md }} />
        <Segmented
          value={settings.cameraFacing}
          options={[
            { id: 'front' as const, label: 'Front (selfie)' },
            ...(cams.includes('back') ? [{ id: 'back' as const, label: 'Back' }] : []),
          ]}
          onChange={v => update({ cameraFacing: v })}
        />
        {(() => { const t = TOGGLES.find(x => x.key === 'mirror')!;
          return <ToggleRow label={t.label} help={t.help} value={settings.mirror} onChange={v => update({ mirror: v })} />; })()}
      </Card>

      <Card>
        <H2>Safety</H2>
        {(() => { const t = TOGGLES.find(x => x.key === 'guardEnabled')!;
          return <ToggleRow label={t.label} help={t.help} value={settings.guardEnabled} onChange={v => update({ guardEnabled: v })} />; })()}
        <Muted style={{ marginTop: space.md }}>
          Volume Up + Volume Down together always pause or resume while AirCursor is running.
        </Muted>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  page: { padding: space.lg, paddingBottom: 40 },
  head: { flexDirection: 'row', alignItems: 'center', marginBottom: space.lg, gap: 12 },
  seg: { flexDirection: 'row', backgroundColor: colors.bg, borderRadius: radius.sm, padding: 4, borderColor: colors.border, borderWidth: 1 },
  segItem: { flex: 1, paddingVertical: 10, alignItems: 'center', borderRadius: radius.sm - 2 },
  segOn: { backgroundColor: colors.accent },
  segText: { color: colors.text, fontWeight: '700' },
  segTextOn: { color: '#04121A' },
  flex: { flex: 1 },
  resetBtn: { paddingVertical: 9 },
});
