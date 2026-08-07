import { router } from 'expo-router';
import { QrCode, ScanLine, Camera } from 'lucide-react-native';
import { useState } from 'react';
import { View, TextInput, Alert, Pressable } from 'react-native';

import { AppText as Text } from '../src/AppText';
import { authedFetch } from '../src/apiClient';
import {
  C,
  PrimaryButton,
  RowCard,
  ScreenShell,
  SectionLabel,
  styles as mockupStyles,
} from '../src/YourEyesMockup';
import { GlassesArt } from '../src/YourEyesMockup'; // This component is also in the mockup

const linkMethods = [
  { title: 'Quét QR', subtitle: 'Quét mã QR trên kính', icon: QrCode },
  { title: 'Nhập serial number', subtitle: 'Nhập số serial của thiết bị', icon: ScanLine },
];

export default function LinkGlassesScreen() {
  const [selected, setSelected] = useState(linkMethods[1].title); // Default to serial number
  const [serial, setSerial] = useState('');
  const [loading, setLoading] = useState(false);
  const isQr = selected === 'Quét QR';

  const handleLinkDevice = async () => {
    if (isQr) {
      Alert.alert('Sắp ra mắt', 'Chức năng quét QR sẽ sớm được cập nhật.');
      return;
    }

    if (!serial.trim()) {
      Alert.alert('Lỗi', 'Vui lòng nhập số serial của thiết bị.');
      return;
    }

    setLoading(true);
    try {
      const response = await authedFetch('/devices/link', {
        method: 'POST',
        body: JSON.stringify({ serial_number: serial }),
      });

      const data = await response.json();

      if (response.ok) {
        Alert.alert('Thành công', 'Thiết bị của bạn đã được liên kết.');
        router.replace('/main'); // Navigate to the main app screen
      } else {
        // authedFetch handles 401, so we only need to care about other errors
        Alert.alert('Liên kết thất bại', data.error || 'Số serial không hợp lệ hoặc đã được sử dụng.');
      }
    } catch (error) {
      console.error('Link device error:', error);
      Alert.alert('Lỗi', 'Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenShell title="Liên kết kính">
      <View style={mockupStyles.linkHero}>
        <GlassesArt width={200} height={104} />
        <Text style={mockupStyles.linkHeroText}>Chọn cách liên kết kính Your Eyes của bạn</Text>
      </View>
      <SectionLabel>Chọn cách liên kết</SectionLabel>
      {linkMethods.map((item) => (
        <RowCard
          key={item.title}
          {...item}
          tone={item.title === selected ? C.cyan : C.muted}
          borderTone={item.title === selected ? C.cyan : undefined}
          onPress={() => setSelected(item.title)}
        />
      ))}

      {isQr ? (
        <Pressable onPress={() => Alert.alert('Sắp ra mắt', 'Chức năng quét QR sẽ sớm được cập nhật.')}>
            <View style={mockupStyles.scanBox}>
            <View style={mockupStyles.scanCorner} />
            <View style={[mockupStyles.scanCorner, { transform: [{ scaleX: -1 }] }]} />
            <View style={[mockupStyles.scanCorner, { transform: [{ scaleY: -1 }] }]} />
            <View style={[mockupStyles.scanCorner, { transform: [{ scaleX: -1 }, { scaleY: -1 }] }]} />
            <Camera size={34} color="#FFFFFF" />
            <Text style={mockupStyles.scanText}>Đưa mã QR trên kính vào khung hình</Text>
          </View>
        </Pressable>
      ) : (
        <View style={mockupStyles.serialBox}>
          <Text style={mockupStyles.serialLabel}>Số serial (in ở gọng kính)</Text>
          <TextInput
            value={serial}
            onChangeText={setSerial}
            placeholder="VD: YE-DEMO-0001"
            placeholderTextColor={C.muted}
            style={mockupStyles.serialInput}
            editable={!loading}
            autoCapitalize="characters"
          />
        </View>
      )}

        <View style={{marginTop: 20}} >
            <PrimaryButton 
                label={loading ? 'Đang xử lý...' : 'Xác nhận liên kết'}
                onPress={handleLinkDevice}
                disabled={loading}
            />
        </View>
    </ScreenShell>
  );
}
