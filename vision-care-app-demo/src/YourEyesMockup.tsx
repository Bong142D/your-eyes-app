import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { Link, router, type Href } from 'expo-router';
import {
  BadgeHelp,
  Bluetooth,
  BookOpen,
  Building2,
  Camera,
  CheckCircle2,
  ChevronRight,
  CreditCard,
  Crown,
  Eye,
  Glasses,
  Headphones,
  HeartPulse,
  History,
  Landmark,
  LockKeyhole,
  Mail,
  MapPin,
  MessageSquareWarning,
  Mic,
  Phone,
  QrCode,
  ScanLine,
  ShieldCheck,
  SlidersHorizontal,
  Smartphone,
  Sparkles,
  Star,
  Tag,
  type LucideIcon,
} from 'lucide-react-native';
import { type ComponentType, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, TextInput, useWindowDimensions, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Defs, Ellipse, G, LinearGradient as SvgGradient, Path, Rect, Stop } from 'react-native-svg';

import { AppText as Text } from './AppText';
import { setIsLinked } from './appState';
import { SafetyScreen } from './SafetyMockup';
import { C, headerIconStyle, notify, R, RowCard, S, ScreenShell, SectionLabel, softShadow } from './ui';

export { C, RowCard, ScreenShell, SectionLabel } from './ui';

const logoAsset = require('../assets/your-eyes/your-eyes-logo-cropped.png');
const logoMarkAsset = require('../assets/your-eyes/your-eyes-mark.png');
const glassesAsset = require('../assets/your-eyes/smart-glasses-hero.png');

type Plan = { name: string; monthly: number | null; firstMonth?: number; features: string[]; highlighted?: boolean; icon: LucideIcon };
function formatVnd(n: number) { return `${n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')}đ`; }
type Device = { name: string; serial: string; battery: number; firmware: string; connected: boolean };
type Transaction = { invoiceId: string; planName: string; amount: string; date: string; status: 'Đã thanh toán' | 'Đang xử lý' | 'Thất bại' | 'Miễn phí' };
type SupportItem = { title: string; subtitle: string; icon: LucideIcon; action: string };

const features = [
  { label: 'AI đồng hành', icon: Sparkles }, { label: 'Lắng nghe', icon: Mic }, { label: 'Nhận biết', icon: Eye },
  { label: 'Hỗ trợ', icon: HeartPulse }, { label: 'Hỗ trợ bạn mỗi ngày', icon: ShieldCheck },
];
const device: Device = { name: 'Kính Your Eyes', serial: 'YE-2A4B-9F70', battery: 82, firmware: 'v2.1.4', connected: true };
const plans: Plan[] = [
  { name: 'Free', monthly: null, features: ['Tính năng cơ bản', 'Giới hạn số lần dùng mỗi ngày'], icon: Sparkles },
  { name: 'Basic', monthly: 99000, firstMonth: 29000, features: ['Bao gồm những tính năng gói cơ bản', 'Tăng giới hạn số lần dùng mỗi ngày', 'Ưu tiên xử lý AI', 'Hỗ trợ trong ngày'], highlighted: true, icon: Star },
  { name: 'Pro', monthly: 199000, firstMonth: 49000, features: ['Bao gồm tất cả tính năng của gói Basic', 'Ưu tiên sử dụng các tính năng mới ra mắt', 'Không giới hạn số lần dùng mỗi ngày', 'Ưu tiên xử lý AI'], icon: Crown },
];
const linkMethods = [
  { title: 'Quét QR', subtitle: 'Quét mã QR trên kính', icon: QrCode },
  { title: 'Nhập serial number', subtitle: 'Nhập số serial của thiết bị', icon: ScanLine },
];
const paymentMethods = [
  { title: 'Thẻ tín dụng / Ghi nợ', subtitle: 'Visa, Mastercard', icon: CreditCard, active: true },
  { title: 'MoMo', subtitle: 'Ví điện tử', icon: Smartphone, active: false },
  { title: 'ZaloPay', subtitle: 'Thanh toán nhanh', icon: HeartPulse, active: false },
  { title: 'Chuyển khoản ngân hàng', subtitle: 'Internet banking', icon: Landmark, active: false },
];
const transactions: Transaction[] = [
  { invoiceId: 'INV-2025-000123', planName: 'Premium Subscription / năm', amount: '990.000đ', date: '23/06/2025 12:00', status: 'Đã thanh toán' },
  { invoiceId: 'INV-2025-000122', planName: 'Premium Subscription / năm', amount: '990.000đ', date: '22/06/2025 10:31', status: 'Đã thanh toán' },
  { invoiceId: 'INV-2025-000121', planName: 'One Day Premium', amount: '247.500đ', date: '21/06/2025 08:18', status: 'Đang xử lý' },
  { invoiceId: 'INV-2025-000120', planName: 'Premium Upgrade', amount: '990.000đ', date: '20/06/2025 18:05', status: 'Thất bại' },
  { invoiceId: 'INV-2025-000119', planName: 'Trial Activation', amount: '0đ', date: '19/06/2025 09:00', status: 'Miễn phí' },
];
const deviceActions = [
  { title: 'Định vị', subtitle: 'Tìm kính gần nhất', icon: MapPin, tone: C.blue },
  { title: 'Khóa thiết bị', subtitle: 'Ngăn truy cập trái phép', icon: ShieldCheck, tone: C.warning },
  { title: 'Báo mất', subtitle: 'Kích hoạt cảnh báo', icon: MessageSquareWarning, tone: C.danger },
  { title: 'Đặt lại thiết bị', subtitle: 'Khôi phục cấu hình', icon: History, tone: C.success },
];
const supportItems: SupportItem[] = [
  { title: 'Hướng dẫn sử dụng', subtitle: 'Tìm hiểu cách sử dụng kính Your Eyes hiệu quả', icon: BookOpen, action: 'Mở' },
  { title: 'Câu hỏi thường gặp (FAQ)', subtitle: 'Giải đáp các thắc mắc phổ biến', icon: BadgeHelp, action: 'Xem' },
  { title: 'Phản hồi lỗi', subtitle: 'Báo cáo lỗi thường gặp hoặc cảnh báo', icon: MessageSquareWarning, action: 'Gửi' },
  { title: 'Gửi yêu cầu hỗ trợ', subtitle: 'Đội ngũ hỗ trợ sẽ liên hệ sớm nhất', icon: Mail, action: 'Tạo' },
];
const routeCards = [
  { number: '1', title: 'Mở đầu', subtitle: 'Chào mừng & giới thiệu', href: '/welcome' },
  { number: '2', title: 'Đăng nhập', subtitle: 'Số điện thoại / Google', href: '/auth' },
  { number: '3', title: 'Đăng ký', subtitle: 'Tạo tài khoản mới', href: '/register' },
  { number: '4', title: 'Xác thực OTP', subtitle: 'Chỉ dùng khi đăng ký bằng SĐT', href: '/otp' },
  { number: '5', title: 'Liên kết kính', subtitle: 'Quét QR hoặc nhập serial', href: '/link-glasses' },
  { number: '6', title: 'Gói dịch vụ', subtitle: 'Chọn gói phù hợp nhu cầu', href: '/packages' },
  { number: '7', title: 'Thanh toán / Gia hạn', subtitle: 'Chọn phương thức thanh toán', href: '/payment' },
  { number: '8', title: 'Trạng thái thuê bao', subtitle: 'Theo dõi tình trạng gói', href: '/subscription' },
  { number: '9', title: 'Lịch sử giao dịch', subtitle: 'Xem hóa đơn & trạng thái', href: '/transactions' },
  { number: '10', title: 'Quản lý thiết bị', subtitle: 'Thông tin & bảo mật thiết bị', href: '/device' },
  { number: '11', title: 'Hỗ trợ người dùng', subtitle: 'Trợ giúp và liên hệ', href: '/support' },
  { number: '12', title: 'An Toàn & SOS', subtitle: 'Theo dõi & báo động khẩn cấp', href: '/main/family' },
] as const;

export function Logo({ compact = false, centered = false }: { compact?: boolean; centered?: boolean }) {
  if (compact) {
    return <View style={styles.logoHorizontal}>
      <Image source={logoMarkAsset} contentFit="contain" style={styles.logoMark} />
      <View style={styles.logoWordmark}>
        <Text style={styles.logoName}>YOUR EYES</Text>
        <Text style={styles.logoTag}>AI SMART GLASSES</Text>
      </View>
    </View>;
  }

  return <View style={[styles.logoWrap, centered && styles.logoCentered]}>
    <Image
      source={logoAsset}
      contentFit="contain"
      style={[styles.logoBitmap, centered && styles.logoBitmapCentered]}
    />
  </View>;
}
export function GlassesArt({ width = 320, height = 170 }: { width?: number; height?: number }) {
  return <View style={{ width, height }}>
    <Image source={glassesAsset} contentFit="contain" style={styles.glassesBitmap} />
  </View>;
}

export function PrimaryButton({ label, href, icon: Icon, compact, disabled, onPress }: { label: string; href?: Href; icon?: LucideIcon; compact?: boolean; disabled?: boolean; onPress?: () => void }) {
  const content = <LinearGradient colors={['#14BCE3', '#52E5B4']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={[styles.primary, compact && styles.primaryCompact, disabled && { opacity: 0.5 }]}>{Icon && <Icon size={compact ? 14 : 18} color="#FFFFFF" />}<Text numberOfLines={1} style={[styles.primaryText, compact && styles.primaryTextCompact]}>{label}</Text><ChevronRight size={compact ? 15 : 18} color="#FFFFFF" /></LinearGradient>;
  if (onPress) return <Pressable disabled={disabled} onPress={onPress}>{content}</Pressable>;
  return href && !compact ? <Link href={href} asChild><Pressable>{content}</Pressable></Link> : <Pressable>{content}</Pressable>;
}
function WelcomeStartButton({ compact }: { compact?: boolean }) {
  const content = <LinearGradient colors={['#77EFC9', '#08B7DE']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={[styles.welcomeButton, compact && styles.welcomeButtonCompact]}>
    <View style={[styles.welcomeButtonCircle, compact && styles.welcomeButtonCircleCompact]}><ChevronRight size={compact ? 18 : 24} color={C.teal} strokeWidth={3} /></View>
    <Text style={[styles.welcomeButtonText, compact && styles.welcomeButtonTextCompact]}>Bắt đầu</Text>
    <ChevronRight size={compact ? 16 : 20} color="#EFFFFB" strokeWidth={2.6} />
  </LinearGradient>;
  return compact ? <Pressable>{content}</Pressable> : <Link href="/register" asChild><Pressable>{content}</Pressable></Link>;
}
function Chip({ label, icon: Icon, tone = C.cyan }: { label: string; icon: LucideIcon; tone?: string }) { return <View style={[styles.chip, { borderColor: `${tone}44` }]}><Icon size={14} color={tone} /><Text numberOfLines={1} style={styles.chipText}>{label}</Text></View>; }
function MiniStat({ label, value, tone = C.cyan }: { label: string; value: string; tone?: string }) { return <View style={styles.miniStat}><Text style={[styles.miniValue, { color: tone }]}>{value}</Text><Text numberOfLines={1} style={styles.miniLabel}>{label}</Text></View>; }
export function WelcomeScreen({ preview = false }: { preview?: boolean }) {
  return <ScreenShell preview={preview} hideBack>
    <View style={[styles.welcomeTop, preview && styles.welcomeTopPreview]}>
      <Logo compact />
      <View style={styles.welcomeBadges}><Chip label="AI đồng hành" icon={Eye} /><Chip label="Voice Support" icon={Mic} tone={C.success} /></View>
    </View>
    <View style={[styles.glassesStage, preview && styles.glassesStagePreview]}>
      <View style={[styles.haloBack, preview && styles.haloBackPreview]} />
      <View style={[styles.haloRing, preview && styles.haloRingPreview]} />
      <View style={[styles.haloRingSmall, preview && styles.haloRingSmallPreview]} />
      <GlassesArt width={preview ? 226 : 346} height={preview ? 126 : 190} />
    </View>
    <View style={[styles.copy, preview && styles.copyPreview]}><Text style={[styles.title, preview && styles.titlePreview]}>Chào mừng đến với <Text style={styles.accent}>Your Eyes</Text></Text><Text style={[styles.body, preview && styles.bodyPreview]}>Trợ lý AI thông minh giúp nghe - nhận biết - hỗ trợ bạn trong cuộc sống hằng ngày.</Text></View>
    <WelcomeStartButton compact={preview} />
    <Text onPress={preview ? undefined : () => router.push('/auth')} style={styles.foot}>Tôi đã có tài khoản</Text>
  </ScreenShell>;
}
export function AuthScreen({ preview = false }: { preview?: boolean }) {
  const login = () => { if (preview) return; setIsLinked(true); router.push('/main'); };
  return <ScreenShell title="Đăng nhập" preview={preview}>
    <View style={styles.authLogoArea}><Logo centered /><Text style={styles.welcome}>Chào mừng bạn trở lại</Text><Text style={styles.note}>Trợ lý AI thông minh cho người khiếm thị</Text></View>
    <View style={styles.methods}>
      <PrimaryButton label="Đăng nhập bằng số điện thoại" icon={Phone} compact={preview} onPress={login} />
      <RowCard title="Đăng nhập với Google" subtitle="Tiếp tục bằng Google" icon={Mail} compact={preview} tone="#EA4335" onPress={preview ? undefined : login} />
    </View>
    <Text style={styles.register}>Chưa có tài khoản? <Text onPress={preview ? undefined : () => router.push('/register')} style={styles.link}>Đăng ký ngay</Text></Text>
  </ScreenShell>;
}
export function RegisterScreen({ preview = false }: { preview?: boolean }) {
  const registerWithGoogle = () => { if (preview) return; setIsLinked(false); router.push('/main'); };
  return <ScreenShell title="Đăng ký" preview={preview}>
    <View style={styles.authLogoArea}><Logo centered /><Text style={styles.welcome}>Tạo tài khoản Your Eyes</Text><Text style={styles.note}>Bắt đầu hành trình cùng trợ lý AI thông minh</Text></View>
    <View style={styles.methods}>
      <PrimaryButton label="Đăng ký bằng số điện thoại" icon={Phone} compact={preview} onPress={preview ? undefined : () => router.push('/otp')} />
      <RowCard title="Đăng ký với Google" subtitle="Tiếp tục bằng Google" icon={Mail} compact={preview} tone="#EA4335" onPress={preview ? undefined : registerWithGoogle} />
    </View>
    <Text style={styles.register}>Đã có tài khoản? <Text onPress={preview ? undefined : () => router.push('/auth')} style={styles.link}>Đăng nhập</Text></Text>
  </ScreenShell>;
}
export function OtpScreen({ preview = false }: { preview?: boolean }) {
  return <ScreenShell title="Xác thực OTP" preview={preview}>
    <View style={styles.center}><View style={[styles.shieldOuter, preview && styles.shieldOuterPreview]}><LinearGradient colors={['#46E2D4', '#0B9FC8']} style={styles.shield}><LockKeyhole size={preview ? 30 : 48} color="#FFFFFF" /></LinearGradient></View><Text style={styles.message}>Chúng tôi đã gửi mã OTP đến</Text><Text style={styles.phone}>(+84) 912 345 678</Text></View>
    <View style={styles.digits}>{['1','2','3','4','5','6'].map((digit) => <View key={digit} style={[styles.digitBox, preview && styles.digitBoxPreview]}><Text style={[styles.digit, preview && styles.digitPreview]}>{digit}</Text></View>)}</View>
    <View style={styles.resend}><Text style={styles.resendText}>Gửi lại mã sau</Text><Text style={styles.timer}>00:45</Text></View>
    <PrimaryButton label="Xác nhận" compact={preview} onPress={preview ? undefined : () => { setIsLinked(false); router.push('/main'); }} />
    <Text onPress={preview ? undefined : () => router.back()} style={styles.change}>Đổi số điện thoại</Text>
  </ScreenShell>;
}
export function LinkGlassesScreen({ preview = false }: { preview?: boolean }) {
  const [selected, setSelected] = useState(linkMethods[0].title);
  const [serial, setSerial] = useState('');
  const isQr = selected === 'Quét QR';
  return <ScreenShell title="Liên kết kính" preview={preview}>
    <View style={[styles.linkHero, preview && styles.linkHeroPreview]}><GlassesArt width={preview ? 150 : 200} height={preview ? 78 : 104} /><Text style={[styles.linkHeroText, preview && styles.smallText9]}>Chọn cách liên kết kính Your Eyes của bạn</Text></View>
    <SectionLabel>Chọn cách liên kết</SectionLabel>
    {linkMethods.map((item) => <RowCard key={item.title} {...item} compact={preview} tone={item.title === selected ? C.cyan : C.muted} borderTone={item.title === selected ? C.cyan : undefined} onPress={preview ? undefined : () => setSelected(item.title)} />)}

    {isQr ? (
      <View style={[styles.scanBox, preview && styles.scanBoxPreview]}>
        <View style={[styles.scanCorner, styles.scanCornerTL]} /><View style={[styles.scanCorner, styles.scanCornerTR]} /><View style={[styles.scanCorner, styles.scanCornerBL]} /><View style={[styles.scanCorner, styles.scanCornerBR]} />
        <Camera size={preview ? 22 : 34} color="#FFFFFF" />
        <Text style={[styles.scanText, preview && styles.smallText9]}>Đưa mã QR trên kính vào khung hình</Text>
      </View>
    ) : (
      <View style={[styles.serialBox, preview && styles.cardPreview9]}>
        <Text style={[styles.serialLabel, preview && styles.smallText9]}>Số serial (in ở gọng kính)</Text>
        <TextInput
          value={serial}
          onChangeText={setSerial}
          placeholder="VD: YE-2A4B-9F70"
          placeholderTextColor={C.muted}
          style={[styles.serialInput, preview && styles.smallText9]}
          editable={!preview}
        />
      </View>
    )}

    {!preview && <PrimaryButton label="Xác nhận liên kết" onPress={() => { setIsLinked(true); router.push('/main'); }} />}
  </ScreenShell>;
}
export function PackagesScreen({ preview = false }: { preview?: boolean }) {
  const [activeCycle, setActiveCycle] = useState('Tháng');
  return <ScreenShell title="Gói dịch vụ" preview={preview}>
    <View style={styles.tabs}>{['Tháng','Năm'].map((tab) => <Pressable key={tab} onPress={() => !preview && setActiveCycle(tab)} style={[styles.tab, tab === activeCycle && styles.activeTab]}><Text style={[styles.tabText, tab === activeCycle && styles.activeTabText]}>{tab}</Text></Pressable>)}</View>
    <View style={styles.planList}>{plans.map((plan) => {
      const Icon = plan.icon;
      const isFree = plan.monthly === null;
      const priceText = isFree ? 'Miễn phí' : activeCycle === 'Tháng' ? formatVnd(plan.monthly as number) : formatVnd((plan.monthly as number) * 12);
      const cycleSuffix = isFree ? '' : activeCycle === 'Tháng' ? '/tháng' : '/năm';
      const cycleLabel = isFree ? 'Miễn phí sử dụng' : activeCycle === 'Tháng' ? 'Thanh toán hàng tháng' : 'Thanh toán hàng năm';
      return <Pressable key={plan.name} onPress={() => !preview && router.push('/payment')} style={[styles.plan, plan.highlighted && styles.highlighted]}>
        <View style={styles.planTop}><View style={styles.planTitleWrap}><Text style={styles.planName}>{plan.name}</Text><Text style={styles.planCycle}>{cycleLabel}</Text></View><View style={[styles.planIcon, plan.highlighted && styles.highlightedIcon]}><Icon size={preview ? 18 : 23} color={plan.highlighted ? '#FFFFFF' : C.teal} fill={plan.highlighted ? '#FFFFFF' : 'transparent'} /></View></View>
        <Text style={styles.price}>{priceText}<Text style={styles.cycle}>{cycleSuffix}</Text></Text>
        {!isFree && activeCycle === 'Tháng' && plan.firstMonth != null && <Text style={styles.firstMonth}>Tháng đầu chỉ {formatVnd(plan.firstMonth)}</Text>}
        {plan.features.map((feature) => <Text key={feature} numberOfLines={2} style={styles.feature}>• {feature}</Text>)}
      </Pressable>;
    })}</View>
    <Text onPress={preview ? undefined : () => notify('Bảng so sánh chi tiết đang được phát triển')} style={styles.compare}>So sánh chi tiết tính năng ›</Text>
  </ScreenShell>;
}
export function PaymentScreen({ preview = false }: { preview?: boolean }) {
  const [selectedMethod, setSelectedMethod] = useState(paymentMethods.find((m) => m.active)?.title ?? paymentMethods[0].title);
  return <ScreenShell title="Thanh toán" preview={preview}>
    <View style={styles.summary}><View><Text style={styles.label}>Gói đã chọn</Text><Text style={styles.planSummary}>Premium Subscription</Text><Text style={styles.priceSummary}>990.000đ <Text style={styles.muted}>/năm</Text></Text></View><View style={styles.star}><Text style={styles.starText}>★</Text></View></View>
    <SectionLabel>Mã giảm giá</SectionLabel><View style={styles.coupon}><Tag size={18} color={C.cyan} /><Text style={styles.couponText}>Nhập mã giảm giá</Text><Text onPress={preview ? undefined : () => notify('Đã áp dụng mã giảm giá')} style={styles.apply}>Áp dụng</Text></View>
    <SectionLabel>Phương thức thanh toán</SectionLabel>{paymentMethods.map((method) => <RowCard key={method.title} title={method.title} subtitle={method.subtitle} icon={method.icon} compact={preview} tone={method.title === selectedMethod ? C.cyan : C.muted} right={<View style={[styles.radio, method.title === selectedMethod && styles.radioActive]} />} onPress={preview ? undefined : () => setSelectedMethod(method.title)} />)}
    <PrimaryButton label="Chuyển sang cổng thanh toán" href="/subscription" compact={preview} />
    <View style={styles.secure}><LockKeyhole size={14} color={C.success} /><Text style={styles.secureText}>Giao dịch được bảo mật với SSL 256-bit</Text></View>
  </ScreenShell>;
}
export function SubscriptionScreen({ preview = false }: { preview?: boolean }) {
  const [reminder, setReminder] = useState(true);
  const statuses = [{ title: 'Còn hạn', date: 'Hết hạn vào 20/07/2025', value: '28', unit: 'còn lại', tone: C.success, bg: '#EDFFF3' }, { title: 'Sắp hết hạn', date: 'Hết hạn vào 04/07/2025', value: '3', unit: 'còn lại', tone: C.warning, bg: '#FFF7EA' }, { title: 'Quá hạn', date: 'Hết hạn từ 15/05/2025', value: '-10', unit: 'ngày', tone: C.danger, bg: '#FFF0F0' }];
  return <ScreenShell title="Trạng thái thuê bao" preview={preview}>
    <View style={styles.statusList}>{statuses.map((status) => <View key={status.title} style={[styles.statusCard, { backgroundColor: status.bg }]}><View style={styles.statusText}><Text style={[styles.statusTitle, { color: status.tone }]}>{status.title}</Text><Text style={styles.statusPlan}>Premium Subscription</Text><Text style={styles.statusDate}>{status.date}</Text></View><View style={[styles.ring, { borderColor: status.tone }]}><Text style={[styles.value, { color: status.tone }]}>{status.value}</Text><Text style={styles.unit}>{status.unit}</Text></View></View>)}</View>
    <View style={styles.renew}><View style={styles.renewTextWrap}><Text style={styles.renewTitle}>Nhắc nhở gia hạn</Text><Text style={styles.renewText}>Chúng tôi sẽ gửi thông báo trước khi gói gần hết hạn.</Text></View><Switch value={reminder} onValueChange={setReminder} trackColor={{ true: C.success, false: '#D1D5DB' }} thumbColor="#FFFFFF" /></View>
    {!preview && <PrimaryButton label="Vào ứng dụng" href="/main" />}
  </ScreenShell>;
}
export function TransactionsScreen({ preview = false }: { preview?: boolean }) {
  const statusColors = { 'Đã thanh toán': C.success, 'Đang xử lý': C.warning, 'Thất bại': C.danger, 'Miễn phí': C.success } as const;
  return <ScreenShell title="Lịch sử giao dịch" preview={preview} right={<Pressable style={headerIconStyle} onPress={preview ? undefined : () => notify('Bộ lọc nâng cao đang được phát triển')}><SlidersHorizontal size={18} color={C.navy} /></Pressable>}>
    <Pressable disabled={preview} onPress={() => notify('Bộ lọc: Tất cả trạng thái')} style={styles.filter}><Text style={styles.filterText}>Tất cả</Text><Text style={styles.filterArrow}>⌄</Text></Pressable>
    <View style={styles.txList}>{transactions.map((item) => <Pressable key={item.invoiceId} disabled={preview} onPress={() => notify(`${item.planName} · ${item.amount}`, item.invoiceId)} style={styles.transaction}><View style={styles.transactionMain}><Text numberOfLines={1} style={styles.invoice}>{item.invoiceId}</Text><Text numberOfLines={1} style={styles.txPlan}>{item.planName}</Text><Text style={styles.date}>{item.date}</Text></View><View style={styles.amountWrap}><Text style={styles.amount}>{item.amount}</Text><Text style={[styles.status, { color: statusColors[item.status] }]}>{item.status}</Text></View></Pressable>)}</View>
    <Text onPress={preview ? undefined : () => notify('Đã tải thêm giao dịch')} style={styles.more}>Kéo xuống để tải thêm</Text>
  </ScreenShell>;
}
export function DeviceScreen({ preview = false }: { preview?: boolean }) {
  return <ScreenShell title="Quản lý thiết bị" preview={preview} right={<Pressable style={headerIconStyle} onPress={preview ? undefined : () => notify('Đang tìm thiết bị Bluetooth...')}><Bluetooth size={18} color={C.navy} /></Pressable>}>
    <View style={styles.deviceHero}><View style={styles.deviceTop}><View><Text style={styles.deviceName}>{device.name}</Text><Text style={styles.online}>● Đã kết nối</Text></View><Text style={styles.battery}>{device.battery}%</Text></View><GlassesArt width={preview ? 178 : 236} height={preview ? 90 : 120} /><Text style={styles.serial}>Serial: {device.serial} · Firmware: {device.firmware}</Text></View>
    <View style={styles.stats}><MiniStat label="Pin" value={`${device.battery}%`} tone={C.success} /><MiniStat label="Bluetooth" value="ON" tone={C.blue} /><MiniStat label="Bảo mật" value="OK" tone={C.success} /></View>
    <View style={styles.gridActions}>{deviceActions.map((action) => <View key={action.title} style={styles.action}><RowCard title={action.title} subtitle={action.subtitle} icon={action.icon} tone={action.tone} compact right={null} onPress={preview ? undefined : () => notify(action.subtitle, action.title)} /></View>)}</View>
    <SectionLabel>Bảo mật</SectionLabel><RowCard title="Mã hóa dữ liệu" subtitle="Đảm bảo sự riêng tư tuyệt đối" icon={CheckCircle2} tone={C.success} compact={preview} right={<CheckCircle2 size={18} color={C.success} />} onPress={preview ? undefined : () => notify('Mã hóa dữ liệu đang bật', 'Bảo mật')} /><RowCard title="Xác thực 2 lớp" subtitle="Tăng cường bảo vệ tài khoản" icon={ShieldCheck} tone={C.success} compact={preview} right={<CheckCircle2 size={18} color={C.success} />} onPress={preview ? undefined : () => notify('Xác thực 2 lớp đang bật', 'Bảo mật')} />
  </ScreenShell>;
}
export function SupportScreen({ preview = false }: { preview?: boolean }) {
  const tones = [C.blue, C.cyan, C.warning, C.teal];
  return <ScreenShell title="Hỗ trợ" preview={preview}>
    <Pressable disabled={preview} onPress={() => notify('Đang gọi 1900 1234...', 'Hotline 24/7')}><LinearGradient colors={['#0C8EC2', '#15C7D8']} style={styles.hotline}><View><Text style={styles.hotlineLabel}>Hotline 24/7</Text><Text style={styles.hotlineNumber}>1900 1234</Text><Text style={styles.hotlineText}>Hỗ trợ nhanh chóng mọi lúc</Text></View><View style={styles.headset}><Headphones size={preview ? 34 : 46} color="#FFFFFF" /></View></LinearGradient></Pressable>
    <View style={styles.supportList}>{supportItems.map((item, index) => <RowCard key={item.title} title={item.title} subtitle={item.subtitle} icon={item.icon} tone={tones[index]} compact={preview} onPress={preview ? undefined : () => notify(item.subtitle, `${item.action}: ${item.title}`)} />)}</View>
  </ScreenShell>;
}
const previews: ComponentType<{ preview?: boolean }>[] = [WelcomeScreen, AuthScreen, RegisterScreen, OtpScreen, LinkGlassesScreen, PackagesScreen, PaymentScreen, SubscriptionScreen, TransactionsScreen, DeviceScreen, SupportScreen, SafetyScreen];

export function PosterBoardScreen() {
  const { width } = useWindowDimensions();
  const isPoster = width >= 980;
  const cardWidth = isPoster ? '18.45%' : width >= 720 ? '30.5%' : '100%';

  return <LinearGradient colors={['#F5FFFE', '#EAFBFF', '#FFFFFF']} style={styles.page}>
    <SafeAreaView style={styles.posterSafe}>
      <ScrollView contentContainerStyle={styles.posterContent} showsVerticalScrollIndicator={false}>
        <View style={styles.posterHero}>
          <View style={styles.posterCopy}>
            <Logo />
            <Text style={styles.kicker}>ỨNG DỤNG QUẢN LÝ & THANH TOÁN</Text>
            <Text style={styles.posterTitle}>Kính thông minh <Text style={styles.titleAccent}>Your Eyes</Text></Text>
            <View style={styles.featureRow}>{features.map((feature) => {
              const Icon = feature.icon;
              return <View key={feature.label} style={styles.posterFeature}><Icon size={18} color={C.cyan} strokeWidth={2.4} /><Text style={styles.posterFeatureText}>{feature.label}</Text></View>;
            })}</View>
          </View>
          <View style={styles.heroArt}>
            <GlassesArt width={isPoster ? 430 : 320} height={isPoster ? 230 : 170} />
          </View>
        </View>

        <View style={styles.previewGrid}>{routeCards.map((card, index) => {
          const Preview = previews[index];
          return <View key={card.href} style={[styles.posterItem, { width: cardWidth }]}>
            <View style={styles.itemHeader}>
              <Text style={styles.number}>{card.number}</Text>
              <View style={styles.itemText}><Text numberOfLines={1} style={styles.itemTitle}>{card.title}</Text><Text numberOfLines={1} style={styles.itemSubtitle}>{card.subtitle}</Text></View>
            </View>
            <Link href={card.href as Href} asChild><Pressable style={styles.phoneFrame}><Preview preview /></Pressable></Link>
          </View>;
        })}</View>

        <View style={styles.footer}>
          <View style={styles.footerItem}><Mic size={26} color={C.cyan} /><Text style={styles.footerText}>Lắng nghe</Text></View>
          <View style={styles.footerItem}><Eye size={26} color={C.cyan} /><Text style={styles.footerText}>Nhận biết</Text></View>
          <View style={styles.footerItem}><HeartPulse size={26} color={C.cyan} /><Text style={styles.footerText}>Hỗ trợ</Text></View>
          <View style={styles.footerItem}><Sparkles size={24} color={C.cyan} /><Text style={styles.domain}>your-eyes.ai</Text></View>
        </View>
      </ScrollView>
    </SafeAreaView>
  </LinearGradient>;
}
export const styles = StyleSheet.create({
  logoWrap: { alignItems: 'center', flexDirection: 'row' }, logoCentered: { justifyContent: 'center' }, logoHorizontal: { alignItems: 'center', alignSelf: 'flex-start', flexDirection: 'row', gap: 8, height: 42 }, logoMark: { height: 35, width: 42 }, logoBitmap: { height: 70, width: 178 }, logoBitmapCentered: { height: 122, width: 190 }, logoWordmark: { justifyContent: 'center' }, logoWordmarkCentered: { alignItems: 'center' }, logoName: { color: '#14244A', fontSize: 13, fontWeight: '900', letterSpacing: 4 }, logoNameCompact: { fontSize: 14, letterSpacing: 1.6 }, logoNameCentered: { fontSize: 22, letterSpacing: 7 }, logoTag: { color: C.muted, fontSize: 7, fontWeight: '800', letterSpacing: 1.8, marginTop: 3 }, glassesBitmap: { height: '100%', width: '100%' },
  primary: { alignItems: 'center', borderRadius: R.pill, flexDirection: 'row', gap: S.sm, justifyContent: 'center', minHeight: 52, paddingHorizontal: S.lg, ...softShadow }, primaryCompact: { minHeight: 38, paddingHorizontal: S.md }, primaryText: { color: '#FFFFFF', flexShrink: 1, fontSize: 15, fontWeight: '800' }, primaryTextCompact: { fontSize: 11 }, welcomeButton: { alignItems: 'center', borderRadius: R.pill, flexDirection: 'row', height: 58, justifyContent: 'space-between', paddingLeft: 7, paddingRight: 19, ...softShadow }, welcomeButtonCompact: { height: 40, paddingLeft: 5, paddingRight: 12 }, welcomeButtonCircle: { alignItems: 'center', backgroundColor: '#FFFFFF', borderRadius: 23, height: 46, justifyContent: 'center', width: 46 }, welcomeButtonCircleCompact: { borderRadius: 16, height: 32, width: 32 }, welcomeButtonText: { color: '#FFFFFF', flex: 1, fontSize: 17, fontWeight: '900', textAlign: 'center' }, welcomeButtonTextCompact: { fontSize: 11 },
  chip: { alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.98)', borderColor: '#E3F6F4', borderRadius: R.pill, borderWidth: 1, flex: 1, flexDirection: 'row', gap: 7, justifyContent: 'center', minHeight: 36, paddingHorizontal: 8, paddingVertical: 7 }, chipText: { color: C.navy, fontSize: 11, fontWeight: '800' },
  miniStat: { alignItems: 'center', backgroundColor: C.mintSoft, borderRadius: R.md, flex: 1, padding: S.md }, miniValue: { fontSize: 20, fontWeight: '900' }, miniLabel: { color: C.muted, fontSize: 10, fontWeight: '700', marginTop: 2 },
  welcomeTop: { backgroundColor: '#FFFFFF', borderRadius: 22, gap: 16, marginHorizontal: -2, paddingHorizontal: 10, paddingTop: 8, paddingBottom: 10 }, welcomeTopPreview: { borderRadius: 13, gap: 9, marginHorizontal: -2, paddingHorizontal: 5, paddingTop: 3, paddingBottom: 5 }, welcomeBadges: { flexDirection: 'row', justifyContent: 'space-between', gap: 12, marginTop: 2 }, glassesStage: { alignItems: 'center', justifyContent: 'center', marginLeft: -20, marginRight: -20, marginTop: 8, marginBottom: 20, minHeight: 218 }, glassesStagePreview: { marginTop: 5, marginBottom: 11, minHeight: 134 }, haloBack: { position: 'absolute', bottom: 8, height: 112, width: 330, borderRadius: 170, backgroundColor: '#D6FFF8' }, haloBackPreview: { bottom: 4, height: 66, width: 205 }, haloRing: { position: 'absolute', bottom: 24, height: 64, width: 312, borderColor: '#14CFEA', borderRadius: 160, borderWidth: 4, opacity: 0.42 }, haloRingPreview: { bottom: 16, height: 39, width: 194, borderWidth: 2 }, haloRingSmall: { position: 'absolute', bottom: 39, height: 34, width: 252, borderColor: '#A7F7EC', borderRadius: 130, borderWidth: 2, opacity: 0.8 }, haloRingSmallPreview: { bottom: 24, height: 21, width: 158, borderWidth: 1 }, top: { gap: S.md }, chips: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.sm }, hero: { alignItems: 'center', backgroundColor: C.surface, borderRadius: R.xl, marginVertical: S.xl, paddingVertical: S.sm, ...softShadow }, heroPreview: { marginVertical: S.md }, copy: { gap: 14, marginBottom: 26, paddingHorizontal: 0 }, copyPreview: { gap: 8, marginBottom: 14 }, title: { color: '#14244A', fontSize: 34, fontWeight: '900', lineHeight: 41 }, titlePreview: { fontSize: 21, lineHeight: 26 }, accent: { color: C.teal }, body: { color: '#7E8EA2', fontSize: 15, fontWeight: '700', lineHeight: 24, maxWidth: 305 }, bodyPreview: { fontSize: 10, lineHeight: 14 }, foot: { color: C.cyan, fontSize: 13, fontWeight: '900', marginTop: 18, textAlign: 'center' },
  authLogoArea: { alignItems: 'center', gap: 8, marginBottom: 22, paddingTop: 26 }, logoArea: { alignItems: 'center', gap: S.sm, marginBottom: S.xl, paddingTop: S.xl }, welcome: { color: C.ink, fontSize: 16, fontWeight: '900', marginTop: S.md, textAlign: 'center' }, note: { color: C.muted, fontSize: 12, fontWeight: '600', textAlign: 'center' }, methods: { gap: S.sm }, register: { color: C.muted, fontSize: 12, fontWeight: '700', marginTop: S.xl, textAlign: 'center' }, link: { color: C.cyan, fontWeight: '900' },
  center: { alignItems: 'center', paddingVertical: S.xl }, shieldOuter: { alignItems: 'center', backgroundColor: '#DDFBF6', borderColor: '#BDF3EA', borderRadius: 26, borderWidth: 1, height: 118, justifyContent: 'center', marginBottom: S.xl, transform: [{ rotate: '45deg' }], width: 118, ...softShadow }, shieldOuterPreview: { height: 82, width: 82 }, shield: { alignItems: 'center', borderRadius: 22, height: 82, justifyContent: 'center', transform: [{ rotate: '-45deg' }], width: 82 }, shieldPreview: { height: 82, width: 82 }, message: { color: C.muted, fontSize: 13, fontWeight: '700' }, phone: { color: C.ink, fontSize: 16, fontWeight: '900', marginTop: 5 }, digits: { flexDirection: 'row', gap: S.sm, justifyContent: 'center', marginBottom: S.xl }, digitBox: { alignItems: 'center', backgroundColor: C.surface, borderColor: '#D9F4F1', borderRadius: R.sm, borderWidth: 1, height: 44, justifyContent: 'center', width: 38 }, digitBoxPreview: { height: 32, width: 27 }, digit: { color: C.ink, fontSize: 20, fontWeight: '900' }, digitPreview: { fontSize: 14 }, resend: { alignItems: 'center', flexDirection: 'row', gap: S.sm, justifyContent: 'center', marginBottom: S.xl }, resendText: { color: C.muted, fontSize: 12, fontWeight: '700' }, timer: { color: C.ink, fontSize: 12, fontWeight: '900' }, change: { color: C.cyan, fontSize: 12, fontWeight: '900', marginTop: S.md, textAlign: 'center' },
  deviceCard: { alignItems: 'center', backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, padding: S.lg, ...softShadow }, cardHead: { alignItems: 'center', alignSelf: 'stretch', flexDirection: 'row', justifyContent: 'space-between' }, deviceName: { color: C.ink, fontSize: 16, fontWeight: '900' }, online: { color: C.success, fontSize: 11, fontWeight: '800', marginTop: 3 }, meta: { alignSelf: 'stretch', flexDirection: 'row', justifyContent: 'space-between' }, metaText: { color: C.muted, fontSize: 11, fontWeight: '800' },
  linkHero: { alignItems: 'center', gap: S.sm, marginBottom: S.lg, paddingVertical: S.md }, linkHeroPreview: { paddingVertical: S.xs }, linkHeroText: { color: C.muted, fontSize: 12, fontWeight: '700', textAlign: 'center' }, smallText9: { fontSize: 9 }, cardPreview9: { padding: S.sm },
  scanBox: { alignItems: 'center', backgroundColor: '#0F1B2E', borderRadius: R.lg, gap: S.sm, justifyContent: 'center', marginTop: S.lg, paddingVertical: 44, position: 'relative' }, scanBoxPreview: { paddingVertical: 20, borderRadius: R.md }, scanText: { color: '#D9F4F1', fontSize: 12, fontWeight: '700', paddingHorizontal: S.xl, textAlign: 'center' }, scanCorner: { borderColor: C.teal, position: 'absolute', height: 26, width: 26 }, scanCornerTL: { borderLeftWidth: 3, borderTopWidth: 3, borderTopLeftRadius: 8, left: 14, top: 14 }, scanCornerTR: { borderRightWidth: 3, borderTopWidth: 3, borderTopRightRadius: 8, right: 14, top: 14 }, scanCornerBL: { borderBottomLeftRadius: 8, borderBottomWidth: 3, borderLeftWidth: 3, bottom: 14, left: 14 }, scanCornerBR: { borderBottomRightRadius: 8, borderBottomWidth: 3, borderRightWidth: 3, bottom: 14, right: 14 },
  serialBox: { backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, marginTop: S.lg, padding: S.lg, ...softShadow }, serialLabel: { color: C.muted, fontSize: 11, fontWeight: '800', marginBottom: S.sm }, serialInput: { borderColor: '#D9F4F1', borderRadius: R.sm, borderWidth: 1, color: C.ink, fontSize: 14, fontWeight: '700', paddingHorizontal: S.md, paddingVertical: S.sm },
  tabs: { backgroundColor: '#E9F8F7', borderRadius: R.pill, flexDirection: 'row', gap: 5, marginBottom: S.lg, padding: 4 }, tab: { alignItems: 'center', borderRadius: R.pill, flex: 1, paddingVertical: 8 }, activeTab: { backgroundColor: C.cyan }, tabText: { color: C.muted, fontSize: 11, fontWeight: '800' }, activeTabText: { color: '#FFFFFF' }, planList: { gap: S.md, marginBottom: S.lg }, plan: { backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, padding: S.lg }, highlighted: { borderColor: C.cyan, borderWidth: 2, ...softShadow }, planTop: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' }, planTitleWrap: { flex: 1 }, planName: { color: C.ink, fontSize: 15, fontWeight: '900' }, planCycle: { color: C.muted, fontSize: 11, fontWeight: '700', marginTop: 2 }, planIcon: { alignItems: 'center', backgroundColor: C.mintSoft, borderRadius: R.md, height: 44, justifyContent: 'center', width: 44 }, highlightedIcon: { backgroundColor: C.cyan }, price: { color: C.navy, fontSize: 18, fontWeight: '900', marginTop: S.md }, cycle: { color: C.muted, fontSize: 12 }, firstMonth: { color: C.success, fontSize: 11, fontWeight: '800', marginTop: 3 }, feature: { color: C.muted, fontSize: 11, fontWeight: '600', lineHeight: 16, marginTop: 4 }, compare: { color: C.cyan, fontSize: 12, fontWeight: '900', marginTop: S.lg, textAlign: 'center' },
  summary: { alignItems: 'center', backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, flexDirection: 'row', justifyContent: 'space-between', padding: S.lg }, label: { color: C.muted, fontSize: 11, fontWeight: '700' }, planSummary: { color: C.ink, fontSize: 15, fontWeight: '900', marginTop: 6 }, priceSummary: { color: C.navy, fontSize: 16, fontWeight: '900', marginTop: 5 }, muted: { color: C.muted, fontSize: 11 }, star: { alignItems: 'center', backgroundColor: C.cyan, borderRadius: R.md, height: 42, justifyContent: 'center', width: 42 }, starText: { color: '#FFFFFF', fontSize: 22 }, coupon: { alignItems: 'center', backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.md, borderWidth: 1, flexDirection: 'row', gap: S.sm, padding: S.md }, couponText: { color: C.muted, flex: 1, fontSize: 12, fontWeight: '700' }, apply: { color: C.cyan, fontSize: 12, fontWeight: '900' }, radio: { borderColor: '#BFDAD7', borderRadius: 10, borderWidth: 2, height: 18, width: 18 }, radioActive: { backgroundColor: C.cyan, borderColor: C.cyan }, secure: { alignItems: 'center', flexDirection: 'row', gap: S.sm, justifyContent: 'center', marginTop: S.lg }, secureText: { color: C.muted, fontSize: 11, fontWeight: '700' },
  statusList: { gap: S.md }, statusCard: { alignItems: 'center', borderRadius: R.lg, flexDirection: 'row', justifyContent: 'space-between', padding: S.lg }, statusText: { flex: 1, minWidth: 0 }, statusTitle: { fontSize: 17, fontWeight: '900' }, statusPlan: { color: C.ink, fontSize: 13, fontWeight: '900', marginTop: 7 }, statusDate: { color: C.muted, fontSize: 11, fontWeight: '700', marginTop: 4 }, ring: { alignItems: 'center', borderRadius: 34, borderWidth: 5, height: 68, justifyContent: 'center', marginLeft: S.md, width: 68 }, value: { fontSize: 18, fontWeight: '900' }, unit: { color: C.muted, fontSize: 8, fontWeight: '800' }, renew: { alignItems: 'center', backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, flexDirection: 'row', gap: S.md, justifyContent: 'space-between', marginTop: S.xl, padding: S.lg }, renewTextWrap: { flex: 1 }, renewTitle: { color: C.ink, fontSize: 14, fontWeight: '900' }, renewText: { color: C.muted, fontSize: 11, fontWeight: '700', lineHeight: 16, marginTop: 4 },
  filter: { alignItems: 'center', flexDirection: 'row', gap: 4, marginBottom: S.md }, filterText: { color: C.ink, fontSize: 13, fontWeight: '900' }, filterArrow: { color: C.muted, fontSize: 13, fontWeight: '900' }, txList: { backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, overflow: 'hidden' }, transaction: { borderBottomColor: '#EEF7F6', borderBottomWidth: 1, flexDirection: 'row', gap: S.md, padding: S.md }, transactionMain: { flex: 1, minWidth: 0 }, invoice: { color: C.ink, fontSize: 13, fontWeight: '900' }, txPlan: { color: C.muted, fontSize: 10, fontWeight: '700', marginTop: 4 }, date: { color: '#9CA9B8', fontSize: 10, fontWeight: '700', marginTop: 4 }, amountWrap: { alignItems: 'flex-end' }, amount: { color: C.ink, fontSize: 12, fontWeight: '900' }, status: { fontSize: 10, fontWeight: '900', marginTop: 9 }, more: { color: C.muted, fontSize: 11, fontWeight: '700', marginTop: S.lg, textAlign: 'center' },
  deviceHero: { alignItems: 'center', backgroundColor: C.surface, borderColor: '#DDF4F1', borderRadius: R.lg, borderWidth: 1, padding: S.lg, ...softShadow }, deviceTop: { alignItems: 'center', alignSelf: 'stretch', flexDirection: 'row', justifyContent: 'space-between' }, battery: { color: C.success, fontSize: 14, fontWeight: '900' }, serial: { color: C.muted, fontSize: 11, fontWeight: '800' }, stats: { flexDirection: 'row', gap: S.sm, marginTop: S.md }, gridActions: { flexDirection: 'row', flexWrap: 'wrap', gap: S.sm, marginTop: S.lg }, action: { flexBasis: '48%', flexGrow: 1 },
  hotline: { alignItems: 'center', borderRadius: R.lg, flexDirection: 'row', justifyContent: 'space-between', marginBottom: S.lg, padding: S.lg, ...softShadow }, hotlineLabel: { color: '#D9FEFF', fontSize: 11, fontWeight: '800' }, hotlineNumber: { color: '#FFFFFF', fontSize: 26, fontWeight: '900', marginTop: 5 }, hotlineText: { color: '#D9FEFF', fontSize: 11, fontWeight: '700', marginTop: 3 }, headset: { alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.16)', borderRadius: 34, height: 68, justifyContent: 'center', width: 68 }, supportList: { gap: S.sm },
  page: { flex: 1 }, posterSafe: { flex: 1, backgroundColor: 'transparent' }, posterContent: { alignSelf: 'center', maxWidth: 1180, paddingHorizontal: 26, paddingTop: 24, paddingBottom: 22, width: '100%' }, posterHero: { alignItems: 'flex-start', flexDirection: 'row', gap: 24, justifyContent: 'space-between', marginBottom: 22, flexWrap: 'wrap' }, posterCopy: { flex: 1.1, minWidth: 430 }, kicker: { color: C.navy, fontSize: 27, fontWeight: '900', letterSpacing: 0.2, marginTop: 18 }, posterTitle: { color: C.cyan, fontSize: 43, fontWeight: '900', lineHeight: 50, marginTop: 4 }, titleAccent: { color: C.teal }, featureRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 18, marginTop: 24 }, posterFeature: { alignItems: 'center', flexDirection: 'row', gap: 7 }, posterFeatureText: { color: C.navy, fontSize: 12, fontWeight: '800' }, heroArt: { alignItems: 'center', flex: 0.9, minWidth: 360, paddingTop: 2 }, previewGrid: { columnGap: 20, flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', rowGap: 18 }, posterItem: { minWidth: 176, maxWidth: 212 }, itemHeader: { alignItems: 'center', flexDirection: 'row', gap: 8, marginBottom: 8, minHeight: 36 }, number: { color: C.cyan, fontSize: 25, fontWeight: '900', textAlign: 'center', width: 32 }, itemText: { flex: 1, minWidth: 0 }, itemTitle: { color: C.ink, fontSize: 12.5, fontWeight: '900' }, itemSubtitle: { color: C.muted, fontSize: 9.5, fontWeight: '700', marginTop: 2 }, phoneFrame: { aspectRatio: 0.49, borderRadius: 28, overflow: 'hidden' }, footer: { alignItems: 'center', flexDirection: 'row', flexWrap: 'wrap', gap: 104, justifyContent: 'center', marginTop: 28 }, footerItem: { alignItems: 'center', flexDirection: 'row', gap: 8 }, footerText: { color: C.navy, fontSize: 14, fontWeight: '900' }, domain: { color: C.teal, fontSize: 14, fontWeight: '900' },
});

















