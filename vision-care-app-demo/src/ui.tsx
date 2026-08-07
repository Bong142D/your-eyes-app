import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { ChevronLeft, ChevronRight, type LucideIcon } from 'lucide-react-native';
import type { ReactNode } from 'react';
import { Alert, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { AppText } from './AppText';

export function notify(message: string, title = 'Thông báo') {
  Alert.alert(title, message);
}

export const C = {
  navy: '#14325B', ink: '#1B2D48', muted: '#6E829A', cyan: '#12BFE7', teal: '#22D3BD',
  mint: '#80F0D0', mintSoft: '#E9FFFA', skySoft: '#E9F8FF', surface: '#FFFFFF', line: '#D6F2F0',
  success: '#24B86E', warning: '#F59E2E', danger: '#EE5D5D', blue: '#1E9EEB', shadow: '#5AA8B2',
};
export const S = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 };
export const R = { sm: 8, md: 12, lg: 18, xl: 26, pill: 999 };
export const softShadow = { shadowColor: C.shadow, shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.16, shadowRadius: 24, elevation: 7 };

function PhoneStatusBar({ compact = false }: { compact?: boolean }) {
  return <View style={[styles.statusBar, compact && styles.statusBarCompact]}>
    <Text style={styles.statusTime}>9:41</Text>
    <View style={styles.statusRight}>
      <View style={styles.signalBars}><View style={styles.signalTiny} /><View style={styles.signalSmall} /><View style={styles.signalTall} /></View>
      <Text style={styles.wifiMark}>⌁</Text>
      <View style={styles.batteryShell}><View style={styles.batteryFill} /></View>
    </View>
  </View>;
}

export function ScreenShell({ title, preview, embedded, hideBack, right, children }: { title?: string; preview?: boolean; embedded?: boolean; hideBack?: boolean; right?: ReactNode; children: ReactNode }) {
  const inner = <>
    <PhoneStatusBar compact={preview} />
    {title && <View style={styles.header}>{!hideBack ? <Pressable style={styles.headerIcon} onPress={() => router.canGoBack() ? router.back() : router.push('/')}><ChevronLeft size={20} color={C.navy} /></Pressable> : <View style={styles.headerIcon} />}<AppText numberOfLines={1} style={styles.headerTitle}>{title}</AppText>{right || <View style={styles.headerIcon} />}</View>}
    <ScrollView bounces={!preview} showsVerticalScrollIndicator={false} contentContainerStyle={[styles.screenContent, preview && styles.previewContent]}>{children}</ScrollView>
  </>;

  if (embedded) return <View style={styles.embeddedSurface}>{inner}</View>;

  return <LinearGradient colors={['#ECFFFC', '#F8FFFF', '#E9FAFF']} style={styles.gradient}>
    <SafeAreaView edges={preview ? [] : ['bottom']} style={styles.safe}>
      <View style={[styles.phoneSurface, preview && styles.previewSurface]}>{inner}</View>
    </SafeAreaView>
  </LinearGradient>;
}

export function RowCard({ title, subtitle, icon: Icon, tone = C.cyan, right, compact, borderTone, onPress }: { title: string; subtitle: string; icon: LucideIcon; tone?: string; right?: ReactNode; compact?: boolean; borderTone?: string; onPress?: () => void }) {
  return <Pressable disabled={!onPress} onPress={onPress} style={({ pressed }) => [styles.rowCard, compact && styles.rowCardCompact, borderTone && { borderColor: `${borderTone}55` }, pressed && styles.rowCardPressed]}>
    <View style={[styles.rowIcon, { backgroundColor: `${tone}15` }]}><Icon size={compact ? 15 : 19} color={tone} /></View>
    <View style={styles.rowText}><AppText numberOfLines={1} style={[styles.rowTitle, compact && styles.smallTitle]}>{title}</AppText><AppText numberOfLines={2} style={[styles.rowSubtitle, compact && styles.smallSubtitle]}>{subtitle}</AppText></View>
    {right === null ? null : right || <ChevronRight size={18} color={C.muted} />}
  </Pressable>;
}

export function SectionLabel({ children }: { children: string }) { return <AppText style={styles.sectionLabel}>{children}</AppText>; }

const styles = StyleSheet.create({
  gradient: { flex: 1 }, safe: { flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#DAF6F3', paddingVertical: 14 }, phoneSurface: { flex: 1, width: '100%', maxWidth: 390, maxHeight: 844, overflow: 'hidden', backgroundColor: C.surface, borderColor: '#CDEFEA', borderWidth: 1, borderRadius: 34, ...softShadow }, previewSurface: { borderRadius: 30, backgroundColor: C.surface, borderColor: '#CFF2EF', borderWidth: 1, ...softShadow }, embeddedSurface: { flex: 1, width: '100%', backgroundColor: C.surface },
  statusBar: { alignItems: 'center', flexDirection: 'row', height: 34, justifyContent: 'space-between', paddingHorizontal: 24, paddingTop: 8 }, statusBarCompact: { height: 24, paddingHorizontal: 16, paddingTop: 4 }, statusTime: { color: '#111827', fontSize: 12, fontWeight: '900' }, statusRight: { alignItems: 'center', flexDirection: 'row', gap: 5 }, signalBars: { alignItems: 'flex-end', flexDirection: 'row', gap: 2, height: 11 }, signalTiny: { backgroundColor: '#111827', borderRadius: 1, height: 4, width: 3 }, signalSmall: { backgroundColor: '#111827', borderRadius: 1, height: 7, width: 3 }, signalTall: { backgroundColor: '#111827', borderRadius: 1, height: 10, width: 3 }, wifiMark: { color: '#111827', fontSize: 11, fontWeight: '900', lineHeight: 12 }, batteryShell: { borderColor: '#111827', borderRadius: 3, borderWidth: 1.4, height: 10, padding: 1, width: 20 }, batteryFill: { backgroundColor: '#111827', borderRadius: 1.5, flex: 1, width: '75%' }, header: { alignItems: 'center', borderBottomColor: '#EEF8F7', borderBottomWidth: 1, flexDirection: 'row', height: 46, paddingHorizontal: S.md }, headerIcon: { alignItems: 'center', height: 34, justifyContent: 'center', width: 34 }, headerTitle: { color: C.ink, flex: 1, fontSize: 15, fontWeight: '900', textAlign: 'center' },
  screenContent: { paddingHorizontal: 20, paddingTop: 14, paddingBottom: 28 }, previewContent: { paddingHorizontal: 10, paddingTop: 8, paddingBottom: 14 },
  rowCard: { alignItems: 'center', backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: 14, borderWidth: 1, flexDirection: 'row', gap: 10, marginBottom: 9, padding: 12, ...softShadow }, rowCardCompact: { gap: 8, padding: 9 }, rowCardPressed: { opacity: 0.6 }, rowIcon: { alignItems: 'center', borderRadius: R.sm, height: 38, justifyContent: 'center', width: 38 }, rowText: { flex: 1, minWidth: 0 }, rowTitle: { color: C.ink, fontSize: 14, fontWeight: '800' }, rowSubtitle: { color: C.muted, fontSize: 11, fontWeight: '600', lineHeight: 15, marginTop: 2 }, smallTitle: { fontSize: 11 }, smallSubtitle: { fontSize: 9, lineHeight: 12 }, sectionLabel: { color: C.ink, fontSize: 14, fontWeight: '900', marginBottom: S.sm, marginTop: S.lg },
});

export const headerIconStyle = styles.headerIcon;
