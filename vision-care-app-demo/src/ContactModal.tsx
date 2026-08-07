import { Check, X } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { View, Modal, TextInput, StyleSheet, Pressable, Switch } from 'react-native';

import { AppText as Text } from './AppText';
import { C, R, S } from './ui';
import { PrimaryButton } from './YourEyesMockup';

export type ContactData = {
  id?: string;
  name: string;
  phone: string;
  is_primary: boolean;
};

type ContactModalProps = {
  isVisible: boolean;
  onClose: () => void;
  onSave: (contact: ContactData) => void;
  initialData?: ContactData | null;
};

export function ContactModal({ isVisible, onClose, onSave, initialData }: ContactModalProps) {
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [isPrimary, setIsPrimary] = useState(false);

  useEffect(() => {
    if (initialData) {
      setName(initialData.name);
      setPhone(initialData.phone);
      setIsPrimary(initialData.is_primary);
    } else {
      // Reset form for new contact
      setName('');
      setPhone('');
      setIsPrimary(false);
    }
  }, [initialData, isVisible]);

  const handleSave = () => {
    onSave({
      id: initialData?.id,
      name,
      phone,
      is_primary: isPrimary,
    });
  };

  return (
    <Modal
      animationType="fade"
      transparent={true}
      visible={isVisible}
      onRequestClose={onClose}
    >
      <View style={styles.centeredView}>
        <View style={styles.modalView}>
          <Pressable style={styles.closeButton} onPress={onClose}>
            <X size={20} color={C.muted} />
          </Pressable>
          <Text style={styles.modalTitle}>
            {initialData ? 'Sửa liên hệ' : 'Thêm liên hệ khẩn cấp'}
          </Text>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Tên liên hệ</Text>
            <TextInput
              value={name}
              onChangeText={setName}
              placeholder="VD: Mẹ"
              style={styles.input}
              placeholderTextColor={C.muted}
            />
          </View>

          <View style={styles.inputGroup}>
            <Text style={styles.label}>Số điện thoại</Text>
            <TextInput
              value={phone}
              onChangeText={setPhone}
              placeholder="0912345678"
              style={styles.input}
              keyboardType="phone-pad"
              placeholderTextColor={C.muted}
            />
          </View>
          
          <View style={styles.switchGroup}>
            <Text style={styles.label}>Đặt làm liên hệ chính</Text>
            <Switch
              trackColor={{ false: '#D1D5DB', true: C.mint }}
              thumbColor="#FFFFFF"
              onValueChange={setIsPrimary}
              value={isPrimary}
            />
          </View>

          <PrimaryButton label="Lưu lại" onPress={handleSave} icon={Check} />
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  centeredView: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
  },
  modalView: {
    margin: S.lg,
    backgroundColor: 'white',
    borderRadius: R.lg,
    padding: S.xl,
    alignItems: 'stretch',
    shadowColor: '#000',
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
    width: '90%',
  },
  modalTitle: {
    marginBottom: S.lg,
    textAlign: 'center',
    fontSize: 18,
    fontWeight: '900',
    color: C.ink,
  },
  closeButton: {
    position: 'absolute',
    top: S.md,
    right: S.md,
    zIndex: 1,
  },
  inputGroup: {
    marginBottom: S.md,
  },
  label: {
    fontSize: 12,
    fontWeight: '700',
    color: C.muted,
    marginBottom: S.sm,
  },
  input: {
    backgroundColor: C.surface,
    borderColor: C.line,
    borderWidth: 1,
    borderRadius: R.sm,
    padding: S.md,
    fontSize: 14,
    color: C.ink,
  },
  switchGroup: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: S.xl,
  }
});
