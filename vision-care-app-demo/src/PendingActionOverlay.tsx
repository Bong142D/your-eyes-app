import { MapPin } from 'lucide-react-native';
import { useEffect, useRef, useState } from 'react';
import { Linking, Modal, Pressable, StyleSheet, View } from 'react-native';

import { AppText as Text } from './AppText';
import { authedFetch } from './apiClient';
import { C, R, S } from './ui';
import { PrimaryButton } from './YourEyesMockup';

// Khoảng poll — thay cho kênh push thật (Expo Go không nhận được remote push, quyết định
// 2026-08-02, xem BACKEND_FLOWS.md §5.1e). Server Kính/backend dispatch xong thì trong vòng
// tối đa POLL_INTERVAL_MS nữa app sẽ tự thấy qua GET /devices/{id}/pending-actions.
const POLL_INTERVAL_MS = 2500;

type PendingAction = {
  request_id: string;
  action: 'call_emergency_contact' | 'call_contact' | 'navigate' | 'book_grab';
  params: Record<string, any>;
  created_at: string;
};

export function PendingActionOverlay() {
  const [deviceId, setDeviceId] = useState<string | null>(null);
  const [current, setCurrent] = useState<PendingAction | null>(null);
  const [busy, setBusy] = useState(false);
  const handledRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    authedFetch('/devices').then(async (res) => {
      if (!res.ok) return;
      const list = await res.json().catch(() => []);
      if (!cancelled && Array.isArray(list) && list.length > 0) setDeviceId(list[0].id);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!deviceId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;

    const poll = async () => {
      try {
        const res = await authedFetch(`/devices/${deviceId}/pending-actions`);
        if (res.ok) {
          const list: PendingAction[] = await res.json();
          const next = list.find((a) => !handledRef.current.has(a.request_id));
          if (next) {
            setCurrent((prev) => prev ?? next); // không thay action đang hiện dở giữa chừng
          }
        }
      } catch {
        // im lặng — lần poll sau thử lại, không làm phiền demo vì lỗi mạng thoáng qua
      }
      if (!cancelled) timer = setTimeout(poll, POLL_INTERVAL_MS);
    };

    poll();
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [deviceId]);

  const report = async (status: string, detail?: string) => {
    if (!current || !deviceId) return;
    handledRef.current.add(current.request_id);
    setBusy(true);
    try {
      await authedFetch(`/devices/${deviceId}/actions/${current.request_id}/report`, {
        method: 'POST',
        body: JSON.stringify({ status, detail }),
      });
    } finally {
      setBusy(false);
      setCurrent(null);
    }
  };

  const handleCancel = () => report('cancelled');

  // Quyết định 2026-08-02 (theo yêu cầu, thay thiết kế "hiện màn xác nhận" ban đầu): luồng gọi
  // (call_emergency_contact/call_contact, kể cả SOS) không hiện màn xác nhận của app nữa —
  // nhận lệnh là mở thẳng app Điện thoại luôn. autoActedRef đảm bảo chỉ mở 1 lần/request_id dù
  // effect có chạy lại (StrictMode). Vẫn còn đúng 1 lần bấm nút gọi trong CHÍNH app Điện thoại —
  // Android không cho gọi thẳng (ACTION_CALL) nếu không có quyền CALL_PHONE + build native
  // riêng, ngoài khả năng của Expo Go.
  const autoActedRef = useRef<Set<string>>(new Set());
  useEffect(() => {
    if (!current) return;
    const isCallAction = current.action === 'call_emergency_contact' || current.action === 'call_contact';
    const phone = current.params.contact_phone;
    if (isCallAction && phone && !autoActedRef.current.has(current.request_id)) {
      autoActedRef.current.add(current.request_id);
      Linking.openURL(`tel:${phone}`).finally(() => report('done'));
    }
  }, [current]);

  const handleConfirmNavigate = async () => {
    const dest = current?.params.destination;
    if (dest) {
      await Linking.openURL(`https://www.google.com/maps/dir/?api=1&destination=${dest.lat},${dest.lng}`);
    }
    await report('done');
  };

  if (!current) return null;

  if (current.action === 'navigate') {
    const dest = current.params.destination || {};
    return (
      <Modal transparent animationType="fade" visible>
        <View style={styles.backdrop}>
          <View style={styles.card}>
            <View style={styles.iconWrap}>
              <MapPin size={28} color={C.cyan} />
            </View>
            <Text style={styles.title}>Chỉ đường</Text>
            <Text style={styles.detail}>{dest.address || `${dest.lat}, ${dest.lng}`}</Text>
            <View style={styles.actions}>
              <Pressable style={styles.cancelBtn} onPress={handleCancel} disabled={busy}>
                <Text style={styles.cancelText}>Huỷ</Text>
              </Pressable>
              <View style={{ flex: 1 }}>
                <PrimaryButton label="Bắt đầu" onPress={handleConfirmNavigate} disabled={busy} />
              </View>
            </View>
          </View>
        </View>
      </Modal>
    );
  }

  if (current.action === 'call_emergency_contact' || current.action === 'call_contact') {
    const phone = current.params.contact_phone;

    if (!phone) {
      // call_contact (tìm trong danh bạ máy) — chưa hỗ trợ trong bản demo này, không có số để
      // tự gọi. Báo thật "no_match" (đúng ý nghĩa status có sẵn) thay vì giả vờ tìm được liên hệ.
      return (
        <Modal transparent animationType="fade" visible>
          <View style={styles.backdrop}>
            <View style={styles.card}>
              <Text style={styles.title}>Không tìm thấy liên hệ</Text>
              <Text style={styles.detail}>
                Kính yêu cầu gọi "{current.params.contact_query}" — tính năng tìm trong danh bạ máy chưa hỗ trợ trong bản demo này.
              </Text>
              <PrimaryButton
                label="Đóng"
                onPress={() => report('no_match', 'Chưa hỗ trợ tìm danh bạ máy trong bản demo.')}
                disabled={busy}
              />
            </View>
          </View>
        </Modal>
      );
    }

    // Có số điện thoại — useEffect ở trên tự mở thẳng app Điện thoại, không hiện gì ở đây
    // (tránh nháy màn hình chờ effect chạy).
    return null;
  }

  // book_grab hoặc action khác — ngoài phạm vi 3 luồng (gọi điện/SOS/chỉ đường) đang làm lần
  // này. Vẫn phải báo lại để không kẹt hàng đợi pending-actions ở lần poll sau.
  return (
    <Modal transparent animationType="fade" visible>
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <Text style={styles.title}>Chưa hỗ trợ</Text>
          <Text style={styles.detail}>Hành động "{current.action}" chưa được hỗ trợ trong bản demo này.</Text>
          <PrimaryButton
            label="Đóng"
            onPress={() => report('failed', 'Action chưa hỗ trợ trong demo')}
            disabled={busy}
          />
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  card: {
    margin: S.lg,
    backgroundColor: 'white',
    borderRadius: R.lg,
    padding: S.xl,
    alignItems: 'center',
    width: '88%',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
  },
  iconWrap: {
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: C.mintSoft,
    borderRadius: R.pill,
    height: 56,
    width: 56,
    marginBottom: S.md,
  },
  title: { fontSize: 16, fontWeight: '900', color: C.ink, textAlign: 'center' },
  detail: { fontSize: 13, fontWeight: '600', color: C.muted, marginTop: S.xs, marginBottom: S.lg, textAlign: 'center' },
  actions: { flexDirection: 'row', gap: S.md, width: '100%', alignItems: 'center' },
  cancelBtn: {
    paddingVertical: S.md,
    paddingHorizontal: S.lg,
    borderRadius: R.pill,
    borderWidth: 1,
    borderColor: C.line,
  },
  cancelText: { color: C.muted, fontSize: 14, fontWeight: '800' },
});
