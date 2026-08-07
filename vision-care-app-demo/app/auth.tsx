import { router } from 'expo-router';
import { Phone, Mail } from 'lucide-react-native';
import { useState } from 'react';
import { View, TextInput, Alert } from 'react-native';

import { AppText as Text } from '../src/AppText';
import { API_BASE_URL } from '../src/apiConfig';
import {
  RowCard,
  ScreenShell,
  C,
} from '../src/ui';
import {
  Logo,
  PrimaryButton,
  styles,
} from '../src/YourEyesMockup';

export default function AuthScreen() {
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLoginWithPhone = async () => {
    if (!phone.trim() || !/^\d{10}$/.test(phone)) {
      Alert.alert('Lỗi', 'Vui lòng nhập số điện thoại hợp lệ (10 chữ số).');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/accounts/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ phone }),
      });

      const data = await response.json();

      if (response.ok) {
        // Navigate to OTP screen, passing phone and purpose
        router.push({ 
          pathname: '/otp', 
          params: { phone, purpose: 'login' } 
        });
      } else {
        Alert.alert('Đăng nhập thất bại', data.error || 'Số điện thoại không tồn tại hoặc đã có lỗi xảy ra.');
      }
    } catch (error) {
      console.error('Login error:', error);
      Alert.alert('Lỗi', 'Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.');
    } finally {
      setLoading(false);
    }
  };

  const loginWithGoogle = () => {
    Alert.alert('Sắp ra mắt', 'Tính năng đăng nhập với Google sẽ sớm được cập nhật.');
  };

  return (
    <ScreenShell title="Đăng nhập">
      <View style={styles.authLogoArea}>
        <Logo centered />
        <Text style={styles.welcome}>Chào mừng bạn trở lại</Text>
        <Text style={styles.note}>Trợ lý AI thông minh cho người khiếm thị</Text>
      </View>

      <View style={styles.serialBox}>
        <Text style={styles.serialLabel}>Số điện thoại</Text>
        <TextInput
          value={phone}
          onChangeText={setPhone}
          placeholder="0912345678"
          placeholderTextColor={C.muted}
          style={styles.serialInput}
          keyboardType="phone-pad"
          editable={!loading}
        />
      </View>

      <View style={{marginTop: 10}}/>

      <PrimaryButton 
        label={loading ? 'Đang xử lý...' : 'Đăng nhập bằng số điện thoại'} 
        icon={Phone} 
        onPress={handleLoginWithPhone} 
        disabled={loading}
      />
      
      <View style={{marginTop: 10}}/>

      <RowCard 
        title="Đăng nhập với Google" 
        subtitle="Tiếp tục bằng Google" 
        icon={Mail} 
        tone="#EA4335" 
        onPress={loginWithGoogle} 
      />

      <Text style={styles.register}>
        Chưa có tài khoản?{' '}
        <Text onPress={() => router.push('/register')} style={styles.link}>
          Đăng ký ngay
        </Text>
      </Text>
    </ScreenShell>
  );
}
