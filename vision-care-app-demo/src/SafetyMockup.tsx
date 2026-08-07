import { LinearGradient } from 'expo-linear-gradient';
import { router, type Href } from 'expo-router';
import { Asterisk, BookOpen, CheckCircle2, Eye, Footprints, Glasses, Headphones, History, Home, MapPin, Phone, Plus, ShieldCheck, Smartphone, Star, type LucideIcon } from 'lucide-react-native';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText as Text } from './AppText';
import { useIsLinked } from './appState';
import { C, notify, R, RowCard, S, ScreenShell, SectionLabel, softShadow } from './ui';

export { C, RowCard, ScreenShell, SectionLabel } from './ui';

type QuickCall = { title: string; subtitle: string; icon: LucideIcon; tone: string; borderTone?: string };
type ActivityEntry = { title: string; time: string; done: boolean };

const homeLinks: { title: string; subtitle: string; icon: LucideIcon; tone: string; href: Href }[] = [
  { title: 'Quản lý thiết bị', subtitle: 'Pin, kết nối & bảo mật kính', icon: Smartphone, tone: C.blue, href: '/device' },
  { title: 'Gói dịch vụ', subtitle: 'Xem & nâng cấp gói đang dùng', icon: Star, tone: C.teal, href: '/packages' },
  { title: 'Trạng thái thuê bao', subtitle: 'Theo dõi ngày hết hạn', icon: ShieldCheck, tone: C.success, href: '/subscription' },
  { title: 'Lịch sử giao dịch', subtitle: 'Hóa đơn & thanh toán', icon: History, tone: C.warning, href: '/transactions' },
  { title: 'Hỗ trợ', subtitle: 'Hotline & câu hỏi thường gặp', icon: Headphones, tone: C.cyan, href: '/support' },
];

const quickCalls: QuickCall[] = [
  { title: 'Gọi Mẹ', subtitle: 'Số điện thoại chính', icon: Phone, tone: C.cyan },
  { title: 'Gọi Anh', subtitle: 'Liên hệ khẩn cấp', icon: Phone, tone: C.cyan },
  { title: 'Gọi 115', subtitle: 'Cấp cứu y tế', icon: Plus, tone: C.danger, borderTone: C.danger },
];
const currentLocation = { address: '123 Đường Trần Hưng Đạo, Quận 1, TP.HCM', status: 'Đang di chuyển', updatedAt: '2 phút trước' };
const activityLog: ActivityEntry[] = [
  { title: 'Đã tới Công viên', time: '08:30', done: true },
  { title: 'Bắt đầu đi dạo', time: '08:00', done: false },
];

const featureList: { title: string; description: string; icon: LucideIcon; tone: string }[] = [
  { title: 'Nhận biết môi trường', description: 'AI mô tả vật thể, người quen và không gian xung quanh theo thời gian thực.', icon: Eye, tone: C.cyan },
  { title: 'Tìm kiếm định vị', description: 'Định vị vị trí hiện tại và dẫn đường an toàn đến điểm đến.', icon: MapPin, tone: C.blue },
  { title: 'Tiếp cận thông tin', description: 'Đọc to văn bản, biển báo, nhãn sản phẩm và tài liệu.', icon: BookOpen, tone: C.teal },
  { title: 'Di chuyển an toàn', description: 'Cảnh báo chướng ngại vật, bậc thang và nguy hiểm phía trước.', icon: Footprints, tone: C.warning },
  { title: 'Sinh hoạt cá nhân', description: 'Nhận diện tiền, màu sắc và vật dụng trong sinh hoạt hằng ngày.', icon: Home, tone: C.success },
];

export function SafetyScreen({ preview = false, embedded = false }: { preview?: boolean; embedded?: boolean }) {
  return <ScreenShell title="AN TOÀN" preview={preview} embedded={embedded}>
    <Pressable disabled={preview} onPress={() => notify('Đã gửi tín hiệu SOS và vị trí của bạn cho người thân!', 'SOS')} style={({ pressed }) => [styles.sos, preview && styles.sosPreview, pressed && styles.sosPressed]}>
      <LinearGradient pointerEvents="none" colors={['#FF8A8A', C.danger]} style={StyleSheet.absoluteFill} />
      <Asterisk size={preview ? 26 : 40} color="#FFFFFF" strokeWidth={2.6} />
      <Text style={[styles.sosText, preview && styles.sosTextPreview]}>SOS</Text>
    </Pressable>
    <Text style={styles.sosHint}>Ấn 3 lần để báo động</Text>

    <SectionLabel>Gọi nhanh</SectionLabel>
    {quickCalls.map((item) => <RowCard key={item.title} title={item.title} subtitle={item.subtitle} icon={item.icon} tone={item.tone} borderTone={item.borderTone} right={null} compact={preview} onPress={preview ? undefined : () => notify(`Đang gọi ${item.title.replace('Gọi ', '')}...`, item.title)} />)}

    <SectionLabel>Theo dõi</SectionLabel>
    <View style={[styles.card, preview && styles.cardPreview]}>
      <View style={styles.locationHead}>
        <MapPin size={preview ? 15 : 19} color={C.cyan} />
        <Text style={[styles.cardLabel, preview && styles.cardLabelPreview]}>VỊ TRÍ HIỆN TẠI</Text>
      </View>
      <Text numberOfLines={2} style={[styles.address, preview && styles.addressPreview]}>{currentLocation.address}</Text>
      <View style={styles.divider} />
      <View style={styles.statusRow}>
        <View style={styles.statusLeft}><View style={styles.statusDot} /><Text style={[styles.statusText, preview && styles.smallText]}>{currentLocation.status}</Text></View>
        <Text style={[styles.statusTime, preview && styles.smallText]}>{currentLocation.updatedAt}</Text>
      </View>
    </View>

    <View style={[styles.card, preview && styles.cardPreview]}>
      <Text style={[styles.cardLabel, preview && styles.cardLabelPreview]}>NHẬT KÝ HOẠT ĐỘNG HÔM NAY</Text>
      {activityLog.map((entry, index) => {
        const Icon = entry.done ? CheckCircle2 : Footprints;
        return <View key={entry.title} style={[styles.logRow, index === activityLog.length - 1 && styles.logRowLast]}>
          <Icon size={preview ? 14 : 18} color={entry.done ? C.success : C.cyan} />
          <Text numberOfLines={1} style={[styles.logTitle, preview && styles.smallText]}>{entry.title}</Text>
          <Text style={[styles.logTime, preview && styles.smallText]}>{entry.time}</Text>
        </View>;
      })}
    </View>
  </ScreenShell>;
}

export function HomeScreen() {
  const isLinked = useIsLinked();
  return <ScreenShell title="Home" hideBack embedded>
    <Text style={styles.homeGreeting}>Chào bạn 👋</Text>
    <Text style={styles.homeSub}>Truy cập nhanh các chức năng của Your Eyes</Text>

    {!isLinked && <View style={styles.unlinkedCard}>
      <View style={styles.unlinkedIcon}><Glasses size={28} color={C.cyan} /></View>
      <Text style={styles.unlinkedTitle}>Bạn chưa liên kết kính Your Eyes</Text>
      <Text style={styles.unlinkedText}>Liên kết kính để dùng đầy đủ tính năng AI đồng hành, theo dõi & an toàn.</Text>
      <Pressable onPress={() => router.push('/link-glasses')} style={styles.unlinkedButton}><Text style={styles.unlinkedButtonText}>Liên kết kính ngay</Text></Pressable>
    </View>}

    <SectionLabel>Quản lý</SectionLabel>
    {homeLinks.map((item) => <RowCard key={item.title} title={item.title} subtitle={item.subtitle} icon={item.icon} tone={item.tone} onPress={() => router.push(item.href)} />)}
  </ScreenShell>;
}

export function FeaturesScreen() {
  return <ScreenShell title="Tính năng" hideBack embedded>
    <Text style={styles.homeGreeting}>Tính năng nổi bật</Text>
    <Text style={styles.homeSub}>Trợ lý AI Your Eyes đồng hành cùng bạn mỗi ngày</Text>
    <View style={styles.featureList}>{featureList.map((feature) => {
      const Icon = feature.icon;
      return <View key={feature.title} style={styles.featureCard}>
        <View style={[styles.featureIcon, { backgroundColor: `${feature.tone}15` }]}><Icon size={22} color={feature.tone} /></View>
        <View style={styles.featureText}>
          <Text style={styles.featureTitle}>{feature.title}</Text>
          <Text numberOfLines={2} style={styles.featureDescription}>{feature.description}</Text>
        </View>
      </View>;
    })}</View>
  </ScreenShell>;
}

export const styles = StyleSheet.create({
  sos: { alignItems: 'center', borderRadius: R.xl, gap: S.sm, justifyContent: 'center', marginTop: S.md, overflow: 'hidden', paddingVertical: 36, ...softShadow },
  sosPreview: { borderRadius: R.lg, paddingVertical: 18 },
  sosPressed: { opacity: 0.85 },
  sosText: { color: '#FFFFFF', fontSize: 26, fontWeight: '900', letterSpacing: 1 },
  sosTextPreview: { fontSize: 15 },
  sosHint: { color: C.muted, fontSize: 12, fontWeight: '700', marginTop: S.sm, marginBottom: S.xl, textAlign: 'center' },
  card: { backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, marginBottom: S.md, padding: S.lg, ...softShadow },
  cardPreview: { borderRadius: R.md, padding: S.sm },
  locationHead: { alignItems: 'center', flexDirection: 'row', gap: S.xs, marginBottom: S.sm },
  cardLabel: { color: C.muted, fontSize: 11, fontWeight: '900', letterSpacing: 0.5 },
  cardLabelPreview: { fontSize: 8 },
  address: { color: C.ink, fontSize: 14, fontWeight: '700', lineHeight: 20 },
  addressPreview: { fontSize: 9, lineHeight: 12 },
  divider: { backgroundColor: '#EEF7F6', height: 1, marginVertical: S.md },
  statusRow: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  statusLeft: { alignItems: 'center', flexDirection: 'row', gap: 6 },
  statusDot: { backgroundColor: C.success, borderRadius: 4, height: 8, width: 8 },
  statusText: { color: C.success, fontSize: 12, fontWeight: '800' },
  statusTime: { color: C.muted, fontSize: 11, fontWeight: '700' },
  smallText: { fontSize: 9 },
  logRow: { alignItems: 'center', borderBottomColor: '#EEF7F6', borderBottomWidth: 1, flexDirection: 'row', gap: S.sm, paddingVertical: S.sm },
  logRowLast: { borderBottomWidth: 0 },
  logTitle: { color: C.ink, flex: 1, fontSize: 13, fontWeight: '700' },
  logTime: { color: C.muted, fontSize: 11, fontWeight: '700' },
  homeGreeting: { color: C.ink, fontSize: 22, fontWeight: '900' },
  homeSub: { color: C.muted, fontSize: 12, fontWeight: '600', marginTop: 4 },
  unlinkedCard: { alignItems: 'center', backgroundColor: C.mintSoft, borderColor: '#BDF3EA', borderRadius: R.lg, borderWidth: 1, marginTop: S.lg, padding: S.lg },
  unlinkedIcon: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: R.pill, height: 56, justifyContent: 'center', marginBottom: S.sm, width: 56 },
  unlinkedTitle: { color: C.ink, fontSize: 15, fontWeight: '900', textAlign: 'center' },
  unlinkedText: { color: C.muted, fontSize: 12, fontWeight: '600', lineHeight: 18, marginTop: 6, textAlign: 'center' },
  unlinkedButton: { backgroundColor: C.cyan, borderRadius: R.pill, marginTop: S.md, paddingHorizontal: S.xl, paddingVertical: S.sm },
  unlinkedButtonText: { color: '#FFFFFF', fontSize: 13, fontWeight: '900' },
  featureList: { gap: S.md, marginTop: S.lg },
  featureCard: { alignItems: 'flex-start', backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, flexDirection: 'row', gap: S.md, padding: S.lg, ...softShadow },
  featureIcon: { alignItems: 'center', borderRadius: R.md, height: 44, justifyContent: 'center', width: 44 },
  featureText: { flex: 1, minWidth: 0 },
  featureTitle: { color: C.ink, fontSize: 14, fontWeight: '900' },
  featureDescription: { color: C.muted, fontSize: 12, fontWeight: '600', lineHeight: 17, marginTop: 4 },
});
