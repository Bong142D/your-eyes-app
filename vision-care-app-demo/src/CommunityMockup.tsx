import { LinearGradient } from 'expo-linear-gradient';
import { Calendar, Plus, Users2, Volume2 } from 'lucide-react-native';
import { Pressable, StyleSheet, View } from 'react-native';

import { AppText as Text } from './AppText';
import { C, notify, R, RowCard, S, ScreenShell, SectionLabel, softShadow } from './ui';

const groups = [
  { title: 'Người mới dùng kính', subtitle: '1.240 thành viên' },
  { title: 'Mẹo sử dụng hàng ngày', subtitle: '890 thành viên' },
  { title: 'Dành cho người thân', subtitle: '540 thành viên' },
];
const posts = [
  { author: 'Cô Lan', time: '2 giờ trước', title: 'Cách chỉnh giọng đọc dễ nghe hơn', excerpt: 'Mình vừa thử đổi tốc độ giọng đọc trong phần Hồ sơ, nghe rõ hơn hẳn khi ra đường đông người...' },
  { author: 'Anh Minh', time: 'Hôm qua', title: 'Kính giúp mình tự đi xe buýt', excerpt: 'Chia sẻ trải nghiệm dùng tính năng nhận biết vật cản khi di chuyển một mình lần đầu tiên...' },
  { author: 'Chị Hoa (người thân)', time: '2 ngày trước', title: 'Mẹo giúp người thân yên tâm hơn', excerpt: 'Mình bật tính năng theo dõi vị trí ở mục An Toàn, giờ cả nhà đỡ lo hơn nhiều...' },
];
const events = [
  { title: 'Hướng dẫn sử dụng kính Your Eyes', date: 'Thứ 7, 26/07 · 09:00', location: 'Trực tuyến qua Zoom' },
  { title: 'Gặp mặt cộng đồng TP.HCM', date: 'Chủ nhật, 03/08 · 14:00', location: 'Q.1, TP.HCM' },
];

export function CommunityScreen() {
  return <ScreenShell title="Cộng đồng" hideBack embedded>
    <LinearGradient colors={['#0C8EC2', '#15C7D8']} style={styles.hero}>
      <View style={styles.heroIcon}><Users2 size={28} color="#FFFFFF" /></View>
      <View style={styles.heroText}>
        <Text style={styles.heroTitle}>Cộng đồng Your Eyes</Text>
        <Text style={styles.heroSub}>12.500 thành viên đang kết nối</Text>
      </View>
    </LinearGradient>

    <Pressable onPress={() => notify('Đăng bài đang được phát triển')} style={styles.compose}>
      <Plus size={16} color={C.cyan} /><Text style={styles.composeText}>Đăng bài mới</Text>
    </Pressable>

    <SectionLabel>Nhóm hỗ trợ</SectionLabel>
    {groups.map((group) => <RowCard key={group.title} title={group.title} subtitle={group.subtitle} icon={Users2} tone={C.cyan} onPress={() => notify(`Đã tham gia nhóm "${group.title}"`)} />)}

    <SectionLabel>Bài viết nổi bật</SectionLabel>
    {posts.map((post) => <View key={post.title} style={styles.postCard}>
      <Text style={styles.postMeta}>{post.author} · {post.time}</Text>
      <Text style={styles.postTitle}>{post.title}</Text>
      <Text numberOfLines={2} style={styles.postExcerpt}>{post.excerpt}</Text>
      <Pressable onPress={() => notify(`Đang đọc: ${post.title}`, 'Nghe bài viết')} style={styles.listenButton}>
        <Volume2 size={16} color={C.cyan} /><Text style={styles.listenText}>Nghe bài viết</Text>
      </Pressable>
    </View>)}

    <SectionLabel>Sự kiện sắp tới</SectionLabel>
    {events.map((event) => <RowCard key={event.title} title={event.title} subtitle={`${event.date} · ${event.location}`} icon={Calendar} tone={C.warning} onPress={() => notify(`Đã lưu sự kiện: ${event.title}`)} />)}
  </ScreenShell>;
}

const styles = StyleSheet.create({
  hero: { alignItems: 'center', borderRadius: R.lg, flexDirection: 'row', gap: S.md, marginBottom: S.md, padding: S.lg, ...softShadow },
  heroIcon: { alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.16)', borderRadius: R.pill, height: 52, justifyContent: 'center', width: 52 },
  heroText: { flex: 1 },
  heroTitle: { color: '#FFFFFF', fontSize: 16, fontWeight: '900' },
  heroSub: { color: '#D9FEFF', fontSize: 12, fontWeight: '700', marginTop: 3 },
  compose: { alignItems: 'center', borderColor: C.cyan, borderRadius: R.md, borderStyle: 'dashed', borderWidth: 1.5, flexDirection: 'row', gap: S.xs, justifyContent: 'center', marginBottom: S.md, paddingVertical: S.sm },
  composeText: { color: C.cyan, fontSize: 13, fontWeight: '800' },
  postCard: { backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, marginBottom: S.md, padding: S.lg, ...softShadow },
  postMeta: { color: C.muted, fontSize: 11, fontWeight: '700' },
  postTitle: { color: C.ink, fontSize: 15, fontWeight: '900', marginTop: 6 },
  postExcerpt: { color: C.muted, fontSize: 12, fontWeight: '600', lineHeight: 18, marginTop: 6 },
  listenButton: { alignItems: 'center', alignSelf: 'flex-start', backgroundColor: C.mintSoft, borderRadius: R.pill, flexDirection: 'row', gap: 6, marginTop: S.md, paddingHorizontal: S.md, paddingVertical: 8 },
  listenText: { color: C.teal, fontSize: 12, fontWeight: '900' },
});
