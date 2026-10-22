import React from 'react';
import {
  Pressable, StyleProp, StyleSheet, Switch, Text, TextStyle, View, ViewStyle,
} from 'react-native';
import Slider from '@react-native-community/slider';
import { colors, radius, space } from '../theme';
import { SliderDef } from '../settings';

export function Card({ children, active, style }: {
  children: React.ReactNode; active?: boolean; style?: StyleProp<ViewStyle>;
}) {
  return <View style={[s.card, active && s.cardActive, style]}>{children}</View>;
}

export function H1({ children }: { children: React.ReactNode }) {
  return <Text style={s.h1}>{children}</Text>;
}
export function H2({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[s.h2, style]}>{children}</Text>;
}
export function Muted({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[s.muted, style]}>{children}</Text>;
}

export function Pill({ text, kind }: { text: string; kind?: 'ok' | 'warn' | 'danger' }) {
  const color = kind === 'ok' ? colors.green : kind === 'warn' ? colors.amber : kind === 'danger' ? colors.red : colors.muted;
  return (
    <View style={[s.pill, { borderColor: color + '88' }]}>
      <Text style={[s.pillText, { color }]}>{text}</Text>
    </View>
  );
}

type BtnKind = 'primary' | 'warn' | 'danger' | 'ghost' | 'success';
export function Button({ title, onPress, kind = 'ghost', disabled, style }: {
  title: string; onPress: () => void; kind?: BtnKind; disabled?: boolean; style?: StyleProp<ViewStyle>;
}) {
  const bg = { primary: colors.accent, success: colors.green, warn: '#2A2110', danger: '#2B1217', ghost: colors.surface2 }[kind];
  const fg = { primary: '#04121A', success: '#04120A', warn: colors.amber, danger: colors.red, ghost: colors.text }[kind];
  const border = { primary: colors.accent, success: colors.green, warn: colors.amber, danger: colors.red, ghost: colors.border }[kind];
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled}
      onPress={onPress}
      style={({ pressed }) => [s.btn, { backgroundColor: bg, borderColor: border, opacity: disabled ? 0.4 : pressed ? 0.8 : 1 }, style]}>
      <Text style={[s.btnText, { color: fg }]}>{title}</Text>
    </Pressable>
  );
}

export function Meter({ label, value, kind, text }: {
  label: string; value: number; kind?: 'ok' | 'warn'; text?: string;
}) {
  const pct = Math.min(Math.max(value, 0), 1) * 100;
  const color = kind === 'ok' ? colors.green : kind === 'warn' ? colors.amber : colors.accent;
  return (
    <View style={{ marginTop: space.sm }}>
      <View style={s.row}>
        <Text style={s.muted}>{label}</Text>
        {text ? <Text style={s.muted}>{text}</Text> : null}
      </View>
      <View style={s.meterTrack}><View style={[s.meterFill, { width: `${pct}%`, backgroundColor: color }]} /></View>
    </View>
  );
}

export function SliderRow({ def, value, onChange }: {
  def: SliderDef; value: number; onChange: (v: number) => void;
}) {
  return (
    <View style={{ marginTop: space.md }}>
      <View style={s.row}>
        <Text style={s.h2}>{def.label}</Text>
        <Text style={[s.h2, { color: colors.accent }]}>{def.format(value)}</Text>
      </View>
      <Text style={s.muted}>{def.help}</Text>
      <Slider
        value={value}
        minimumValue={def.min}
        maximumValue={def.max}
        step={def.step}
        minimumTrackTintColor={colors.accent}
        maximumTrackTintColor={colors.border}
        thumbTintColor="#FFFFFF"
        onValueChange={v => onChange(Math.round(v * 1000) / 1000)}
        accessibilityLabel={def.label}
      />
    </View>
  );
}

export function ToggleRow({ label, help, value, onChange }: {
  label: string; help: string; value: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <View style={[s.row, { marginTop: space.md }]}>
      <View style={s.toggleText}>
        <Text style={s.h2}>{label}</Text>
        <Text style={s.muted}>{help}</Text>
      </View>
      <Switch
        value={value}
        onValueChange={onChange}
        trackColor={{ true: colors.accent, false: colors.border }}
        thumbColor="#FFFFFF"
        accessibilityLabel={label}
      />
    </View>
  );
}

export const s = StyleSheet.create({
  card: {
    backgroundColor: colors.surface, borderColor: colors.border, borderWidth: 1,
    borderRadius: radius.lg, padding: space.lg, marginBottom: space.md,
  },
  cardActive: { borderColor: colors.accent, backgroundColor: colors.surface2 },
  h1: { color: colors.text, fontSize: 26, fontWeight: '800' },
  h2: { color: colors.text, fontSize: 15, fontWeight: '700' },
  muted: { color: colors.muted, fontSize: 13, marginTop: 2 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  pill: { borderWidth: 1, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 3, backgroundColor: colors.surface2 },
  pillText: { fontSize: 12, fontWeight: '700' },
  btn: { borderWidth: 1, borderRadius: radius.sm + 2, paddingVertical: 13, paddingHorizontal: space.lg, alignItems: 'center' },
  btnText: { fontSize: 15, fontWeight: '800' },
  meterTrack: { height: 8, borderRadius: 4, backgroundColor: colors.border, marginTop: 4, overflow: 'hidden' },
  meterFill: { height: 8, borderRadius: 4 },
  toggleText: { flex: 1, paddingRight: space.md },
});
