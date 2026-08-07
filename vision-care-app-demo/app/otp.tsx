import { router, useLocalSearchParams } from 'expo-router';
import { LockKeyhole } from 'lucide-react-native';
import { useState } from 'react';
import { View, TextInput, Alert, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';

import { AppText as Text } from '../src/AppText';
import { API_BASE_URL } from '../src/apiConfig';
import { saveToken } from '../src/auth';
import {
  PrimaryButton,
  ScreenShell,
  styles as mockupStyles, // Import with an alias to avoid conflict
  C,
} from '../src/YourEyesMockup';

export default function OtpScreen() {
  const { phone, purpose = 'register' } = useLocalSearchParams<{ phone: string, purpose?: 'login' | 'register' }>();
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);

  const handleVerifyOtp = async () => {
    if (!code || code.length !== 6) {
      Alert.alert('Lỗi', 'Vui lòng nhập mã OTP gồm 6 chữ số.');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/accounts/verify-otp`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          phone,
          code,
          purpose, // Use the purpose from params
        }),
      });

      const data = await response.json();

      if (response.ok && data.token) {
        await saveToken(data.token);
        // Replace to prevent going back to OTP screen
        router.replace('/main'); 
      } else {
        Alert.alert('Xác thực thất bại', data.error || 'Mã OTP không đúng hoặc đã hết hạn.');
      }
    } catch (error) {
      console.error('OTP verification error:', error);
      Alert.alert('Lỗi', 'Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenShell title="Xác thực OTP">
      <View style={mockupStyles.center}>
        <View style={mockupStyles.shieldOuter}>
          <LinearGradient colors={['#46E2D4', '#0B9FC8']} style={mockupStyles.shield}>
            <LockKeyhole size={48} color="#FFFFFF" />
          </LinearGradient>
        </View>
        <Text style={mockupStyles.message}>Chúng tôi đã gửi mã OTP đến</Text>
        <Text style={mockupStyles.phone}>(+84) {phone}</Text>
      </View>
      
      <View style={mockupStyles.serialBox}>
        <Text style={mockupStyles.serialLabel}>Mã OTP</Text>
        <TextInput
          value={code}
          onChangeText={setCode}
          placeholder="123456"
          placeholderTextColor={C.muted}
          style={[mockupStyles.serialInput, {textAlign: 'center', fontSize: 20, letterSpacing: 5}]}
          keyboardType="number-pad"
          maxLength={6}
          editable={!loading}
        />
      </View>
      
      <View style={{marginTop: 16, marginBottom: 16}}>
        <Text style={mockupStyles.resendText}>Chưa nhận được mã? <Text style={mockupStyles.link}>Gửi lại</Text></Text>
      </View>

      <PrimaryButton
        label={loading ? 'Đang xác thực...' : 'Xác nhận'}
        onPress={handleVerifyOtp}
        disabled={loading}
      />
      <Text onPress={() => router.back()} style={mockupStyles.change}>
        Đổi số điện thoại
      </Text>
    </ScreenShell>
  );
}
