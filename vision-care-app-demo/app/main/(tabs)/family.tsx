import { LinearGradient } from 'expo-linear-gradient';
import { Asterisk, Footprints, MapPin, Phone, Plus, CheckCircle2 } from 'lucide-react-native';
import { useCallback, useEffect, useState } from 'react';
import { View, Pressable, ActivityIndicator, Alert, StyleSheet } from 'react-native';

import { AppText as Text } from '../../../src/AppText';
import { authedFetch } from '../../../src/apiClient';
import { ContactModal, type ContactData } from '../../../src/ContactModal';
import { PrimaryButton } from '../../../src/YourEyesMockup'; // PrimaryButton is in mockup file
import {
  C,
  RowCard,
  ScreenShell,
  SectionLabel,
  styles as mockupStyles,
} from '../../../src/SafetyMockup';

// Define the type for an emergency contact from the backend
type EmergencyContact = {
  id: string;
  name: string;
  phone: string;
  is_primary: boolean;
};

// Keep the static tracking data for now
const currentLocation = { address: '123 Đường Trần Hưng Đạo, Quận 1, TP.HCM', status: 'Đang di chuyển', updatedAt: '2 phút trước' };
const activityLog = [
  { title: 'Đã tới Công viên', time: '08:30', done: true },
  { title: 'Bắt đầu đi dạo', time: '08:00', done: false },
];

export default function FamilyTab() {
  const [contacts, setContacts] = useState<EmergencyContact[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalVisible, setModalVisible] = useState(false);
  const [editingContact, setEditingContact] = useState<EmergencyContact | null>(null);

  const fetchContacts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await authedFetch('/emergency-contacts');
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Failed to fetch contacts');
      }
      const data: EmergencyContact[] = await response.json();
      setContacts(data);
    } catch (error) {
      console.error('Fetch contacts error:', error);
      Alert.alert('Lỗi', 'Không thể tải danh sách liên hệ khẩn cấp.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchContacts();
  }, [fetchContacts]);

  const handleOpenModal = (contact: EmergencyContact | null) => {
    setEditingContact(contact);
    setModalVisible(true);
  };

  const handleSaveContact = async (contactData: ContactData) => {
    const isEditing = !!contactData.id;
    const url = isEditing ? `/emergency-contacts/${contactData.id}` : '/emergency-contacts';
    const method = isEditing ? 'PATCH' : 'POST';

    try {
      const response = await authedFetch(url, {
        method: method,
        body: JSON.stringify({
          name: contactData.name,
          phone: contactData.phone,
          is_primary: contactData.is_primary,
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || 'Lưu liên hệ thất bại');
      }
      
      setModalVisible(false);
      await fetchContacts(); // Refresh list
      Alert.alert('Thành công', 'Đã lưu liên hệ khẩn cấp.');

    } catch (error: any) {
      Alert.alert('Lỗi', error.message);
    }
  };

  const handleDeleteContact = async (contactId: string) => {
    Alert.alert(
      'Xác nhận xóa',
      'Bạn có chắc chắn muốn xóa liên hệ này?',
      [
        { text: 'Hủy', style: 'cancel' },
        {
          text: 'Xóa',
          style: 'destructive',
          onPress: async () => {
            try {
              const response = await authedFetch(`/emergency-contacts/${contactId}`, { method: 'DELETE' });
              if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.error || 'Xóa liên hệ thất bại');
              }
              await fetchContacts(); // Refresh list
              Alert.alert('Thành công', 'Đã xóa liên hệ.');
            } catch (error: any) {
              Alert.alert('Lỗi', error.message);
            }
          },
        },
      ]
    );
  };

  const handleContactPress = (contact: EmergencyContact) => {
    Alert.alert(
      contact.name,
      'Chọn một hành động',
      [
        { text: 'Sửa', onPress: () => handleOpenModal(contact) },
        { text: 'Xóa', style: 'destructive', onPress: () => handleDeleteContact(contact.id) },
        { text: 'Hủy', style: 'cancel' },
      ]
    )
  };

  const renderQuickCalls = () => {
    if (loading) {
      return <ActivityIndicator color={C.cyan} style={{ marginVertical: 20 }} />;
    }
    if (contacts.length === 0) {
      return <Text style={{ textAlign: 'center', color: C.muted, marginVertical: 20 }}>Chưa có liên hệ khẩn cấp nào.</Text>;
    }
    return contacts.map((contact) => (
      <RowCard
        key={contact.id}
        title={contact.name}
        subtitle={contact.phone}
        icon={Phone}
        tone={contact.is_primary ? C.teal : C.cyan}
        borderTone={contact.is_primary ? C.teal : undefined}
        right={null}
        onPress={() => handleContactPress(contact)}
      />
    ));
  };

  return (
    <ScreenShell title="AN TOÀN" embedded>
      <ContactModal 
        isVisible={isModalVisible}
        onClose={() => setModalVisible(false)}
        onSave={handleSaveContact}
        initialData={editingContact}
      />

      <Pressable onPress={() => { /* Implement real SOS trigger */ }} style={({ pressed }) => [mockupStyles.sos, pressed && mockupStyles.sosPressed]}>
        <LinearGradient pointerEvents="none" colors={['#FF8A8A', C.danger]} style={StyleSheet.absoluteFill} />
        <Asterisk size={40} color="#FFFFFF" strokeWidth={2.6} />
        <Text style={mockupStyles.sosText}>SOS</Text>
      </Pressable>
      <Text style={mockupStyles.sosHint}>Ấn 3 lần để báo động</Text>

      <SectionLabel>Gọi nhanh (Liên hệ khẩn cấp)</SectionLabel>
      {renderQuickCalls()}
      <View style={{marginTop: 10, alignItems: 'center'}}>
        <PrimaryButton label="Thêm liên hệ" icon={Plus} onPress={() => handleOpenModal(null)} compact />
      </View>

      <SectionLabel>Theo dõi</SectionLabel>
      <View style={mockupStyles.card}>
        <View style={mockupStyles.locationHead}>
          <MapPin size={19} color={C.cyan} />
          <Text style={mockupStyles.cardLabel}>VỊ TRÍ HIỆN TẠI</Text>
        </View>
        <Text numberOfLines={2} style={mockupStyles.address}>{currentLocation.address}</Text>
        <View style={mockupStyles.divider} />
        <View style={mockupStyles.statusRow}>
          <View style={mockupStyles.statusLeft}><View style={mockupStyles.statusDot} /><Text style={mockupStyles.statusText}>{currentLocation.status}</Text></View>
          <Text style={mockupStyles.statusTime}>{currentLocation.updatedAt}</Text>
        </View>
      </View>

      <View style={mockupStyles.card}>
        <Text style={mockupStyles.cardLabel}>NHẬT KÝ HOẠT ĐỘNG HÔM NAY</Text>
        {activityLog.map((entry, index) => {
          const Icon = entry.done ? CheckCircle2 : Footprints;
          return <View key={entry.title} style={[mockupStyles.logRow, index === activityLog.length - 1 && mockupStyles.logRowLast]}>
            <Icon size={18} color={entry.done ? C.success : C.cyan} />
            <Text numberOfLines={1} style={mockupStyles.logTitle}>{entry.title}</Text>
            <Text style={mockupStyles.logTime}>{entry.time}</Text>
          </View>;
        })}
      </View>
    </ScreenShell>
  );
}
