import { router } from 'expo-router';
import { Contrast, Headphones, LogOut, Phone, Plus, Smartphone, Star, Type, User, Vibrate, Volume2 } from 'lucide-react-native';
import { useState } from 'react';
import { Pressable, StyleSheet, Switch, View } from 'react-native';

import { FONT_SIZE_OPTIONS, setFontSizeOption, setHighContrast, useFontSizeOption, useHighContrast } from './a11y';
import { AppText as Text } from './AppText';
import { C, notify, R, RowCard, S, ScreenShell, SectionLabel, softShadow } from './ui';

type Contact = { name: string; phone: string };

const contacts: Contact[] = [
  { name: 'Mẹ', phone: '090 111 2222' },
  { name: 'Anh', phone: '090 333 4444' },
];

function OptionChips({ options, value, onChange }: { options: string[]; value: string; onChange: (value: string) => void }) {
  return <View style={styles.chipsRow}>
    {options.map((opt) => <Pressable key={opt} onPress={() => onChange(opt)} style={[styles.chip, opt === value && styles.chipActive]}>
      <Text style={[styles.chipText, opt === value && styles.chipTextActive]}>{opt}</Text>
    </Pressable>)}
  </View>;
}

export function ProfileScreen() {
  const fontSize = useFontSizeOption();
  const highContrast = useHighContrast();
  const [voice, setVoice] = useState('Giọng Nữ');
  const [haptics, setHaptics] = useState(true);

  return <ScreenShell title="Hồ sơ" hideBack embedded>
    <View style={styles.header}>
      <View style={styles.avatar}><User size={30} color={C.cyan} /></View>
      <View style={styles.headerText}>
        <Text style={styles.name}>Nguyễn Văn A</Text>
        <Text style={styles.phone}>090 123 4567</Text>
      </View>
      <Pressable onPress={() => notify('Chỉnh sửa hồ sơ đang được phát triển')} style={styles.editButton}><Text style={styles.editButtonText}>Sửa</Text></Pressable>
    </View>

    <SectionLabel>Trợ năng</SectionLabel>
    <View style={styles.card}>
      <View style={styles.settingLeft}><Type size={18} color={C.cyan} /><Text style={styles.settingLabel}>Cỡ chữ</Text></View>
      <OptionChips options={[...FONT_SIZE_OPTIONS]} value={fontSize} onChange={(value) => setFontSizeOption(value as typeof FONT_SIZE_OPTIONS[number])} />
      <View style={styles.divider} />
      <View style={styles.settingLeft}><Volume2 size={18} color={C.cyan} /><Text style={styles.settingLabel}>Giọng đọc</Text></View>
      <OptionChips options={['Giọng Nữ', 'Giọng Nam']} value={voice} onChange={setVoice} />
      <View style={styles.divider} />
      <View style={styles.settingRow}>
        <View style={styles.settingLeft}><Contrast size={18} color={C.cyan} /><Text style={styles.settingLabel}>Tương phản cao</Text></View>
        <Switch value={highContrast} onValueChange={(value) => setHighContrast(value)} trackColor={{ true: C.success, false: '#D1D5DB' }} thumbColor="#FFFFFF" />
      </View>
      <View style={styles.divider} />
      <View style={styles.settingRow}>
        <View style={styles.settingLeft}><Vibrate size={18} color={C.cyan} /><Text style={styles.settingLabel}>Phản hồi rung</Text></View>
        <Switch value={haptics} onValueChange={setHaptics} trackColor={{ true: C.success, false: '#D1D5DB' }} thumbColor="#FFFFFF" />
      </View>
    </View>

    <SectionLabel>Người thân & liên hệ khẩn cấp</SectionLabel>
    {contacts.map((contact) => <RowCard key={contact.name} title={contact.name} subtitle={contact.phone} icon={Phone} tone={C.cyan} onPress={() => notify(`Chỉnh sửa liên hệ ${contact.name}`)} />)}
    <Pressable onPress={() => notify('Thêm liên hệ khẩn cấp đang được phát triển')} style={styles.addContact}><Plus size={16} color={C.cyan} /><Text style={styles.addContactText}>Thêm liên hệ</Text></Pressable>

    <SectionLabel>Tài khoản</SectionLabel>
    <RowCard title="Gói dịch vụ" subtitle="Xem & nâng cấp gói đang dùng" icon={Star} tone={C.teal} onPress={() => router.push('/packages')} />
    <RowCard title="Thiết bị liên kết" subtitle="Quản lý kính Your Eyes" icon={Smartphone} tone={C.blue} onPress={() => router.push('/device')} />
    <RowCard title="Hỗ trợ" subtitle="Hotline & câu hỏi thường gặp" icon={Headphones} tone={C.cyan} onPress={() => router.push('/support')} />

    <Pressable onPress={() => { notify('Đã đăng xuất'); router.push('/auth'); }} style={styles.logout}>
      <LogOut size={18} color={C.danger} />
      <Text style={styles.logoutText}>Đăng xuất</Text>
    </Pressable>
  </ScreenShell>;
}

const styles = StyleSheet.create({
  header: { alignItems: 'center', flexDirection: 'row', gap: S.md, marginBottom: S.sm },
  avatar: { alignItems: 'center', backgroundColor: C.mintSoft, borderRadius: R.pill, height: 60, justifyContent: 'center', width: 60 },
  headerText: { flex: 1 },
  name: { color: C.ink, fontSize: 18, fontWeight: '900' },
  phone: { color: C.muted, fontSize: 12, fontWeight: '700', marginTop: 2 },
  editButton: { backgroundColor: C.mintSoft, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: S.sm },
  editButtonText: { color: C.teal, fontSize: 12, fontWeight: '900' },
  card: { backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, marginBottom: S.md, padding: S.lg, ...softShadow },
  settingRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  settingLeft: { alignItems: 'center', flexDirection: 'row', gap: S.sm },
  settingLabel: { color: C.ink, fontSize: 14, fontWeight: '800' },
  divider: { backgroundColor: '#EEF7F6', height: 1, marginVertical: S.md },
  chipsRow: { flexDirection: 'row', gap: S.sm, marginTop: S.sm },
  chip: { backgroundColor: C.mintSoft, borderRadius: R.pill, paddingHorizontal: S.md, paddingVertical: 8 },
  chipActive: { backgroundColor: C.cyan },
  chipText: { color: C.teal, fontSize: 12, fontWeight: '800' },
  chipTextActive: { color: '#FFFFFF' },
  addContact: { alignItems: 'center', borderColor: C.cyan, borderRadius: R.md, borderStyle: 'dashed', borderWidth: 1.5, flexDirection: 'row', gap: S.xs, justifyContent: 'center', marginBottom: S.lg, paddingVertical: S.sm },
  addContactText: { color: C.cyan, fontSize: 13, fontWeight: '800' },
  logout: { alignItems: 'center', borderColor: C.danger, borderRadius: R.pill, borderWidth: 1.5, flexDirection: 'row', gap: S.sm, justifyContent: 'center', marginTop: S.lg, paddingVertical: S.md },
  logoutText: { color: C.danger, fontSize: 14, fontWeight: '900' },
});
