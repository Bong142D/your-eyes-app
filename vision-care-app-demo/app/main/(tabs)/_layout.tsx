import { LinearGradient } from 'expo-linear-gradient';
import { Tabs } from 'expo-router';
import { Home, Sparkles, User, Users, Users2, type LucideIcon } from 'lucide-react-native';
import { type ColorValue, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { PendingActionOverlay } from '../../../src/PendingActionOverlay';
import { C } from '../../../src/ui';

function TabIcon({ Icon, color, focused }: { Icon: LucideIcon; color: ColorValue; focused: boolean }) {
  return <View style={{ alignItems: 'center', backgroundColor: focused ? C.mintSoft : 'transparent', borderRadius: 999, justifyContent: 'center', height: 38, width: 38 }}>
    <Icon size={20} color={color as string} />
  </View>;
}

export default function TabsLayout() {
  return <LinearGradient colors={['#ECFFFC', '#F8FFFF', '#E9FAFF']} style={{ flex: 1 }}>
    <SafeAreaView edges={['bottom']} style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: '#DAF6F3', paddingVertical: 14 }}>
      <View style={{ flex: 1, width: '100%', maxWidth: 390, maxHeight: 844, overflow: 'hidden', borderColor: '#CDEFEA', borderWidth: 1, borderRadius: 34, shadowColor: C.shadow, shadowOffset: { width: 0, height: 10 }, shadowOpacity: 0.16, shadowRadius: 24, elevation: 7 }}>
        <Tabs screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: C.cyan,
          tabBarInactiveTintColor: C.muted,
          tabBarLabelStyle: { fontSize: 11, fontWeight: '800' },
          tabBarStyle: { borderTopColor: '#E3F6F4', height: 64, paddingBottom: 8, paddingTop: 6 },
        }}>
          <Tabs.Screen name="index" options={{ title: 'Home', tabBarIcon: ({ color, focused }) => <TabIcon Icon={Home} color={color} focused={focused} /> }} />
          <Tabs.Screen name="features" options={{ title: 'Features', tabBarIcon: ({ color, focused }) => <TabIcon Icon={Sparkles} color={color} focused={focused} /> }} />
          <Tabs.Screen name="family" options={{ title: 'Family', tabBarIcon: ({ color, focused }) => <TabIcon Icon={Users} color={color} focused={focused} /> }} />
          <Tabs.Screen name="community" options={{ title: 'Community', tabBarIcon: ({ color, focused }) => <TabIcon Icon={Users2} color={color} focused={focused} /> }} />
          <Tabs.Screen name="profile" options={{ title: 'Profile', tabBarIcon: ({ color, focused }) => <TabIcon Icon={User} color={color} focused={focused} /> }} />
        </Tabs>
      </View>
    </SafeAreaView>
    <PendingActionOverlay />
  </LinearGradient>;
}
