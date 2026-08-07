import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { View, Switch, ActivityIndicator, Alert } from 'react-native';

import { AppText as Text } from '../src/AppText';
import { authedFetch } from '../src/apiClient';
import {
  C,
  ScreenShell,
  PrimaryButton,
  styles as mockupStyles,
} from '../src/YourEyesMockup';

type SubscriptionStatus = {
  tier: string;
  purchased_tier: string;
  expires_at: string | null;
  status: 'active' | 'expiring_soon' | 'expired';
};

// Map API status to UI colors and text
const statusMap = {
  active: { title: 'Còn hạn', tone: C.success, bg: '#EDFFF3' },
  expiring_soon: { title: 'Sắp hết hạn', tone: C.warning, bg: '#FFF7EA' },
  expired: { title: 'Đã hết hạn', tone: C.danger, bg: '#FFF0F0' },
};

export default function SubscriptionScreen() {
  const [subscription, setSubscription] = useState<SubscriptionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [reminder, setReminder] = useState(true); // Keep as local UI state

  useEffect(() => {
    const fetchSubscription = async () => {
      try {
        setLoading(true);
        const response = await authedFetch('/subscription');
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({}));
          throw new Error(errorData.error || 'Failed to fetch subscription status');
        }
        const data: SubscriptionStatus = await response.json();
        setSubscription(data);
      } catch (error: any) {
        Alert.alert('Lỗi', error.message);
      } finally {
        setLoading(false);
      }
    };
    fetchSubscription();
  }, []);

  const renderStatusCard = () => {
    if (loading) {
      return <ActivityIndicator size="large" color={C.cyan} style={{ margin: 40 }} />;
    }

    if (!subscription) {
      return <Text style={{ textAlign: 'center', color: C.muted, margin: 40 }}>Không thể tải thông tin gói cước.</Text>;
    }

    const uiProps = statusMap[subscription.status] || statusMap.expired;
    const expiresText = subscription.expires_at ? `Hết hạn vào ${subscription.expires_at}` : 'Không có ngày hết hạn';

    return (
      <View style={[mockupStyles.statusCard, { backgroundColor: uiProps.bg }]}>
        <View style={mockupStyles.statusText}>
          <Text style={[mockupStyles.statusTitle, { color: uiProps.tone }]}>
            {uiProps.title}
          </Text>
          <Text style={mockupStyles.statusPlan}>
            Gói {subscription.tier.charAt(0).toUpperCase() + subscription.tier.slice(1)}
          </Text>
          <Text style={mockupStyles.statusDate}>
            {expiresText}
          </Text>
        </View>
        {/* The ring with days remaining is complex to calculate, so we simplify for now */}
      </View>
    );
  };

  return (
    <ScreenShell title="Trạng thái thuê bao">
      {renderStatusCard()}

      <View style={mockupStyles.renew}>
        <View style={mockupStyles.renewTextWrap}>
          <Text style={mockupStyles.renewTitle}>Nhắc nhở gia hạn</Text>
          <Text style={mockupStyles.renewText}>Chúng tôi sẽ gửi thông báo trước khi gói gần hết hạn.</Text>
        </View>
        <Switch 
          value={reminder} 
          onValueChange={setReminder} 
          trackColor={{ true: C.success, false: '#D1D5DB' }} 
          thumbColor="#FFFFFF" 
        />
      </View>
      
      <View style={{marginTop: 20}}>
        <PrimaryButton label="Vào ứng dụng" onPress={() => router.replace('/main')} />
      </View>
    </ScreenShell>
  );
}
