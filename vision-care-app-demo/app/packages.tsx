import { router } from 'expo-router';
import { Crown, Sparkles, Star, LucideIcon } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { View, Pressable, ActivityIndicator, Alert } from 'react-native';

import { AppText as Text } from '../src/AppText';
import { API_BASE_URL } from '../src/apiConfig';
import { ScreenShell, styles as mockupStyles, C } from '../src/YourEyesMockup';

// Helper to map tier names from backend to icons
const iconMap: { [key: string]: LucideIcon } = {
  free: Sparkles,
  basic: Star,
  pro: Crown,
  default: Sparkles,
};

// Define a type for the plan data coming from the API
type ApiPlan = {
  tier: string;
  monthly_price: number;
  yearly_price: number;
  quota_limit: number;
  allowed_intents: string[];
};

function formatVnd(n: number) {
  return `${n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.')}đ`;
}

export default function PackagesScreen() {
  const [activeCycle, setActiveCycle] = useState<'monthly' | 'yearly'>('monthly');
  const [plans, setPlans] = useState<ApiPlan[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchPackages = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/packages`);
        if (!response.ok) {
          throw new Error('Failed to fetch packages');
        }
        const data: ApiPlan[] = await response.json();
        setPlans(data);
      } catch (error) {
        console.error('Fetch packages error:', error);
        Alert.alert('Lỗi', 'Không thể tải danh sách các gói cước. Vui lòng thử lại sau.');
      } finally {
        setLoading(false);
      }
    };

    fetchPackages();
  }, []);

  const handleSelectPlan = (plan: ApiPlan) => {
    // Navigate to payment screen, passing plan details
    // Note: The payment screen is not yet connected, this is a placeholder
    router.push({
      pathname: '/payment',
      params: { tier: plan.tier, cycle: activeCycle },
    });
  };

  if (loading) {
    return (
      <ScreenShell title="Gói dịch vụ">
        <ActivityIndicator size="large" color={C.cyan} style={{ marginTop: 50 }} />
      </ScreenShell>
    );
  }

  return (
    <ScreenShell title="Gói dịch vụ">
      <View style={mockupStyles.tabs}>
        {['monthly', 'yearly'].map((cycle) => (
          <Pressable
            key={cycle}
            onPress={() => setActiveCycle(cycle as 'monthly' | 'yearly')}
            style={[mockupStyles.tab, cycle === activeCycle && mockupStyles.activeTab]}
          >
            <Text style={[mockupStyles.tabText, cycle === activeCycle && mockupStyles.activeTabText]}>
              {cycle === 'monthly' ? 'Tháng' : 'Năm'}
            </Text>
          </Pressable>
        ))}
      </View>
      <View style={mockupStyles.planList}>
        {plans.map((plan) => {
          const Icon = iconMap[plan.tier] || iconMap.default;
          const isFree = plan.monthly_price === 0;
          const price = activeCycle === 'monthly' ? plan.monthly_price : plan.yearly_price;
          const priceText = isFree ? 'Miễn phí' : formatVnd(price);
          const cycleSuffix = isFree ? '' : activeCycle === 'monthly' ? '/tháng' : '/năm';
          const cycleLabel = isFree ? 'Miễn phí sử dụng' : activeCycle === 'monthly' ? 'Thanh toán hàng tháng' : 'Thanh toán hàng năm';

          // A simple way to highlight the 'pro' plan
          const isHighlighted = plan.tier === 'pro';

          return (
            <Pressable
              key={plan.tier}
              onPress={() => handleSelectPlan(plan)}
              style={[mockupStyles.plan, isHighlighted && mockupStyles.highlighted]}
            >
              <View style={mockupStyles.planTop}>
                <View style={mockupStyles.planTitleWrap}>
                  <Text style={mockupStyles.planName}>{plan.tier.charAt(0).toUpperCase() + plan.tier.slice(1)}</Text>
                  <Text style={mockupStyles.planCycle}>{cycleLabel}</Text>
                </View>
                <View style={[mockupStyles.planIcon, isHighlighted && mockupStyles.highlightedIcon]}>
                  <Icon size={23} color={isHighlighted ? '#FFFFFF' : C.teal} fill={isHighlighted ? '#FFFFFF' : 'transparent'} />
                </View>
              </View>
              <Text style={mockupStyles.price}>
                {priceText}
                <Text style={mockupStyles.cycle}>{cycleSuffix}</Text>
              </Text>
              <Text style={mockupStyles.feature}>• {plan.quota_limit} lượt dùng AI/ngày</Text>
              {plan.allowed_intents.map((intent) => (
                <Text key={intent} numberOfLines={2} style={mockupStyles.feature}>
                  • {intent}
                </Text>
              ))}
            </Pressable>
          );
        })}
      </View>
      <Text style={mockupStyles.compare}>So sánh chi tiết tính năng ›</Text>
    </ScreenShell>
  );
}
