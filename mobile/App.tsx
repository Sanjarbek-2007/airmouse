import React, { useState } from 'react';
import { Pressable, StatusBar, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { SettingsProvider } from './src/hooks/useSettings';
import { useAirCursor } from './src/hooks/useAirCursor';
import { GesturesScreen } from './src/screens/GesturesScreen';
import { GuideScreen } from './src/screens/GuideScreen';
import { HomeScreen } from './src/screens/HomeScreen';
import { SettingsScreen } from './src/screens/SettingsScreen';
import { colors } from './src/theme';

const TABS = [
  { id: 'home', label: 'Home', icon: '◉' },
  { id: 'gestures', label: 'Gestures', icon: '✋' },
  { id: 'settings', label: 'Settings', icon: '⚙' },
  { id: 'guide', label: 'Guide', icon: '📖' },
] as const;
type TabId = (typeof TABS)[number]['id'];

function Shell() {
  const insets = useSafeAreaInsets();
  const { status, refresh } = useAirCursor();
  const [tab, setTab] = useState<TabId>('home');

  return (
    <View style={[styles.root, { paddingTop: insets.top }]}>
      <StatusBar barStyle="light-content" />
      <View style={styles.body}>
        {tab === 'home' && <HomeScreen status={status} refresh={refresh} />}
        {tab === 'gestures' && <GesturesScreen status={status} />}
        {tab === 'settings' && <SettingsScreen />}
        {tab === 'guide' && <GuideScreen />}
      </View>
      <View style={[styles.tabs, { paddingBottom: Math.max(insets.bottom, 8) }]}>
        {TABS.map(t => (
          <Pressable key={t.id} style={styles.tab} onPress={() => setTab(t.id)}
            accessibilityRole="tab" accessibilityState={{ selected: tab === t.id }}>
            <Text style={[styles.icon, tab === t.id && styles.on]}>{t.icon}</Text>
            <Text style={[styles.label, tab === t.id && styles.on]}>{t.label}</Text>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <SettingsProvider>
        <Shell />
      </SettingsProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.bg },
  body: { flex: 1 },
  tabs: { flexDirection: 'row', backgroundColor: colors.surface, borderTopColor: colors.border, borderTopWidth: 1, paddingTop: 8 },
  tab: { flex: 1, alignItems: 'center', gap: 2 },
  icon: { fontSize: 20, color: colors.muted },
  label: { fontSize: 11, fontWeight: '700', color: colors.muted },
  on: { color: colors.accent },
});
