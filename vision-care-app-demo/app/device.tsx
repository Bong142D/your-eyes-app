import { router } from 'expo-router';
import {
  Bluetooth,
  CheckCircle2,
  History,
  LockKeyhole,
  MessageSquareWarning,
  ShieldCheck,
  type LucideIcon,
} from 'lucide-react-native';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, View } from 'react-native';

import { AppText as Text } from '../src/AppText';
import { authedFetch } from '../src/apiClient';
import { OtpConfirmModal } from '../src/OtpConfirmModal';
import { headerIconStyle, notify } from '../src/ui';
import {
  C,
  GlassesArt,
  PrimaryButton,
  RowCard,
  ScreenShell,
  SectionLabel,
  styles as mockupStyles,
} from '../src/YourEyesMockup';

type DeviceStatus = 'active' | 'locked' | 'lost' | 'replaced';

type DeviceInfo = {
  id: string;
  serial_number: string;
  status: DeviceStatus;
  battery: number | null;
  firmware: string | null;
  last_seen_bluetooth_at: string | null;
  last_seen_cellular_at: string | null;
  paired_at: string | null;
};

const STATUS_INFO: Record<DeviceStatus, { label: string; tone: string }> = {
  active: { label: 'Đang hoạt động', tone: C.success },
  locked: { label: 'Đã khóa', tone: C.warning },
  lost: { label: 'Đã báo mất', tone: C.danger },
  replaced: { label: 'Đã thay thế', tone: C.muted },
};

function MiniStat({ label, value, tone = C.cyan }: { label: string; value: string; tone?: string }) {
  return (
    <View style={mockupStyles.miniStat}>
      <Text style={[mockupStyles.miniValue, { color: tone }]}>{value}</Text>
      <Text numberOfLines={1} style={mockupStyles.miniLabel}>{label}</Text>
    </View>
  );
}

export default function DeviceScreen() {
  const [device, setDevice] = useState<DeviceInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [otpLoading, setOtpLoading] = useState(false);
  const [otpVisible, setOtpVisible] = useState(false);
  const [pendingOtpAction, setPendingOtpAction] = useState<'lock' | 'report-lost' | null>(null);

  const fetchDevice = useCallback(async () => {
    try {
      const response = await authedFetch('/devices');
      if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error || 'Không thể tải thông tin thiết bị.');
      }
      const data: DeviceInfo[] = await response.json();
      setDevice(data.length > 0 ? data[0] : null);
    } catch (error: any) {
      Alert.alert('Lỗi', error.message || 'Không thể kết nối đến máy chủ.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDevice();
  }, [fetchDevice]);

  const runSimpleAction = (action: 'unlock' | 'recover' | 'reset', confirmMessage: string, successMessage: string) => {
    if (!device) return;
    Alert.alert('Xác nhận', confirmMessage, [
      { text: 'Hủy', style: 'cancel' },
      {
        text: 'Đồng ý',
        onPress: async () => {
          setActionLoading(true);
          try {
            const response = await authedFetch(`/devices/${device.id}/${action}`, { method: 'POST' });
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
              Alert.alert('Thất bại', data.error || 'Không thể thực hiện thao tác.');
              return;
            }
            await fetchDevice();
            Alert.alert('Thành công', successMessage);
          } catch (error) {
            Alert.alert('Lỗi', 'Không thể kết nối đến máy chủ.');
          } finally {
            setActionLoading(false);
          }
        },
      },
    ]);
  };

  const startOtpAction = async (action: 'lock' | 'report-lost') => {
    if (!device) return;
    setActionLoading(true);
    try {
      const response = await authedFetch(`/devices/${device.id}/request-action-otp`, { method: 'POST' });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        Alert.alert('Lỗi', data.error || 'Không thể gửi mã OTP.');
        return;
      }
      setPendingOtpAction(action);
      setOtpVisible(true);
    } catch (error) {
      Alert.alert('Lỗi', 'Không thể kết nối đến máy chủ.');
    } finally {
      setActionLoading(false);
    }
  };

  const confirmOtpAction = async (code: string) => {
    if (!device || !pendingOtpAction) return;
    setOtpLoading(true);
    try {
      const response = await authedFetch(`/devices/${device.id}/${pendingOtpAction}`, {
        method: 'POST',
        body: JSON.stringify({ otp_code: code }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        Alert.alert('Thất bại', data.error || 'Mã OTP không đúng hoặc đã hết hạn.');
        return;
      }
      setOtpVisible(false);
      setPendingOtpAction(null);
      await fetchDevice();
      Alert.alert('Thành công', pendingOtpAction === 'lock' ? 'Đã khóa thiết bị.' : 'Đã báo mất thiết bị.');
    } catch (error) {
      Alert.alert('Lỗi', 'Không thể kết nối đến máy chủ.');
    } finally {
      setOtpLoading(false);
    }
  };

  const actions: { title: string; subtitle: string; icon: LucideIcon; tone: string; onPress: () => void }[] = [];
  if (device?.status === 'active') {
    actions.push({ title: 'Khóa thiết bị', subtitle: 'Ngăn truy cập trái phép', icon: ShieldCheck, tone: C.warning, onPress: () => startOtpAction('lock') });
    actions.push({ title: 'Báo mất', subtitle: 'Kích hoạt cảnh báo mất kính', icon: MessageSquareWarning, tone: C.danger, onPress: () => startOtpAction('report-lost') });
    actions.push({ title: 'Đặt lại thiết bị', subtitle: 'Khôi phục cấu hình gốc', icon: History, tone: C.success, onPress: () => runSimpleAction('reset', 'Đặt lại thiết bị về cấu hình gốc?', 'Đã đặt lại thiết bị.') });
  } else if (device?.status === 'locked') {
    actions.push({ title: 'Mở khóa', subtitle: 'Cho phép sử dụng trở lại', icon: LockKeyhole, tone: C.blue, onPress: () => runSimpleAction('unlock', 'Mở khóa thiết bị?', 'Đã mở khóa thiết bị.') });
    actions.push({ title: 'Báo mất', subtitle: 'Kích hoạt cảnh báo mất kính', icon: MessageSquareWarning, tone: C.danger, onPress: () => startOtpAction('report-lost') });
    actions.push({ title: 'Đặt lại thiết bị', subtitle: 'Khôi phục cấu hình gốc', icon: History, tone: C.success, onPress: () => runSimpleAction('reset', 'Đặt lại thiết bị về cấu hình gốc?', 'Đã đặt lại thiết bị.') });
  } else if (device?.status === 'lost') {
    actions.push({ title: 'Khôi phục', subtitle: 'Đánh dấu đã tìm lại thiết bị', icon: CheckCircle2, tone: C.success, onPress: () => runSimpleAction('recover', 'Đánh dấu đã tìm lại thiết bị?', 'Đã khôi phục thiết bị.') });
    actions.push({ title: 'Đặt lại thiết bị', subtitle: 'Khôi phục cấu hình gốc', icon: History, tone: C.success, onPress: () => runSimpleAction('reset', 'Đặt lại thiết bị về cấu hình gốc?', 'Đã đặt lại thiết bị.') });
  }

  const headerRight = (
    <Pressable style={headerIconStyle} onPress={() => notify('Đang tìm thiết bị Bluetooth...')}>
      <Bluetooth size={18} color={C.navy} />
    </Pressable>
  );

  if (loading) {
    return (
      <ScreenShell title="Quản lý thiết bị" right={headerRight}>
        <ActivityIndicator color={C.cyan} style={{ marginVertical: 40 }} />
      </ScreenShell>
    );
  }

  if (!device) {
    return (
      <ScreenShell title="Quản lý thiết bị" right={headerRight}>
        <View style={localStyles.emptyState}>
          <Text style={localStyles.emptyText}>Bạn chưa liên kết thiết bị nào.</Text>
          <View style={{ marginTop: 16 }}>
            <PrimaryButton label="Liên kết kính" onPress={() => router.push('/link-glasses')} />
          </View>
        </View>
      </ScreenShell>
    );
  }

  const status = STATUS_INFO[device.status];

  return (
    <ScreenShell title="Quản lý thiết bị" right={headerRight}>
      <View style={mockupStyles.deviceHero}>
        <View style={mockupStyles.deviceTop}>
          <View>
            <Text style={mockupStyles.deviceName}>Kính Your Eyes</Text>
            <Text style={[mockupStyles.online, { color: status.tone }]}>● {status.label}</Text>
          </View>
          <Text style={mockupStyles.battery}>{device.battery != null ? `${device.battery}%` : '—'}</Text>
        </View>
        <GlassesArt width={236} height={120} />
        <Text style={mockupStyles.serial}>
          Serial: {device.serial_number} · Firmware: {device.firmware || 'Chưa rõ'}
        </Text>
      </View>

      <View style={mockupStyles.stats}>
        <MiniStat label="Pin" value={device.battery != null ? `${device.battery}%` : '—'} tone={C.success} />
        <MiniStat label="Trạng thái" value={status.label} tone={status.tone} />
        <MiniStat label="Bảo mật" value="OK" tone={C.success} />
      </View>

      {actions.length > 0 && (
        <View style={mockupStyles.gridActions}>
          {actions.map((action) => (
            <View key={action.title} style={mockupStyles.action}>
              <RowCard
                title={action.title}
                subtitle={action.subtitle}
                icon={action.icon}
                tone={action.tone}
                compact
                right={null}
                onPress={actionLoading ? undefined : action.onPress}
              />
            </View>
          ))}
        </View>
      )}

      {device.status === 'replaced' && (
        <Text style={localStyles.replacedNote}>Thiết bị này đã được thay thế bằng kính mới.</Text>
      )}

      <SectionLabel>Thông tin kết nối</SectionLabel>
      <View style={localStyles.infoCard}>
        <Text style={localStyles.infoRow}>Bluetooth gần nhất: {device.last_seen_bluetooth_at || 'Chưa có dữ liệu'}</Text>
        <Text style={localStyles.infoRow}>Mạng di động gần nhất: {device.last_seen_cellular_at || 'Chưa có dữ liệu'}</Text>
        <Text style={localStyles.infoRow}>Liên kết lúc: {device.paired_at || 'Chưa có dữ liệu'}</Text>
      </View>

      <OtpConfirmModal
        isVisible={otpVisible}
        title={pendingOtpAction === 'lock' ? 'Xác thực khóa thiết bị' : 'Xác thực báo mất thiết bị'}
        message="Nhập mã OTP đã gửi tới số điện thoại của bạn để xác nhận."
        loading={otpLoading}
        onClose={() => {
          setOtpVisible(false);
          setPendingOtpAction(null);
        }}
        onConfirm={confirmOtpAction}
      />
    </ScreenShell>
  );
}

const localStyles = StyleSheet.create({
  emptyState: { alignItems: 'center', paddingVertical: 60 },
  emptyText: { color: C.muted, fontSize: 13, fontWeight: '700', textAlign: 'center' },
  replacedNote: { color: C.muted, fontSize: 12, fontWeight: '700', textAlign: 'center', marginTop: 12 },
  infoCard: {
    backgroundColor: C.surface,
    borderColor: '#DDF4F1',
    borderRadius: 14,
    borderWidth: 1,
    padding: 14,
    gap: 8,
  },
  infoRow: { color: C.muted, fontSize: 12, fontWeight: '700' },
});
