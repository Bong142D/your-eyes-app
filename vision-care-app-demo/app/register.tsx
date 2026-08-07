import { router } from 'expo-router';
import { Phone, Mail } from 'lucide-react-native';
import { useState } from 'react';
import { View, TextInput, Alert } from 'react-native';

import { AppText as Text } from '../src/AppText';
import { API_BASE_URL } from '../src/apiConfig';
// Import necessary components and styles from their actual files
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

export default function RegisterScreen() {
  const [phone, setPhone] = useState('');
  const [loading, setLoading] = useState(false);

  const handleRegisterWithPhone = async () => {
    // Basic validation
    if (!phone.trim() || !/^\d{10}$/.test(phone)) {
      Alert.alert('Lỗi', 'Vui lòng nhập số điện thoại hợp lệ (10 chữ số).');
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/accounts/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ phone }),
      });

      const data = await response.json();

      if (response.ok) {
        // Navigate to OTP screen, passing phone number along
        router.push({ pathname: '/otp', params: { phone } });
      } else {
        // Show error message from backend
        Alert.alert('Đăng ký thất bại', data.error || 'Đã có lỗi xảy ra. Vui lòng thử lại.');
      }
    } catch (error) {
      console.error('Registration error:', error);
      Alert.alert('Lỗi', 'Không thể kết nối đến máy chủ. Vui lòng kiểm tra lại kết nối mạng.');
    } finally {
      setLoading(false);
    }
  };
  
  // Mock function for Google Sign-In for now
  const registerWithGoogle = () => {
    Alert.alert('Sắp ra mắt', 'Tính năng đăng ký với Google sẽ sớm được cập nhật.');
  };

  return (
    <ScreenShell title="Đăng ký">
      <View style={styles.authLogoArea}>
        <Logo centered />
        <Text style={styles.welcome}>Tạo tài khoản Your Eyes</Text>
        <Text style={styles.note}>Bắt đầu hành trình cùng trợ lý AI thông minh</Text>
      </View>

      {/* Custom input for phone number */}
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
        label={loading ? 'Đang xử lý...' : 'Đăng ký bằng số điện thoại'} 
        icon={Phone} 
        onPress={handleRegisterWithPhone} 
        disabled={loading}
      />
      
      <View style={{marginTop: 10}}/>

      <RowCard 
        title="Đăng ký với Google" 
        subtitle="Tiếp tục bằng Google" 
        icon={Mail} 
        tone="#EA4335" 
        onPress={registerWithGoogle} 
      />

      <Text style={styles.register}>
        Đã có tài khoản?{' '}
        <Text onPress={() => router.push('/auth')} style={styles.link}>
          Đăng nhập
        </Text>
      </Text>
    </ScreenShell>
  );
}

