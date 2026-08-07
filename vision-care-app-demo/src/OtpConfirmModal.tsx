import { LockKeyhole, X } from 'lucide-react-native';
import { useEffect, useState } from 'react';
import { View, Modal, TextInput, StyleSheet, Pressable } from 'react-native';

import { AppText as Text } from './AppText';
import { C, R, S } from './ui';
import { PrimaryButton } from './YourEyesMockup';

type OtpConfirmModalProps = {
  isVisible: boolean;
  title: string;
  message: string;
  loading?: boolean;
  onClose: () => void;
  onConfirm: (code: string) => void;
};

export function OtpConfirmModal({ isVisible, title, message, loading, onClose, onConfirm }: OtpConfirmModalProps) {
  const [code, setCode] = useState('');

  useEffect(() => {
    if (isVisible) setCode('');
  }, [isVisible]);

  return (
    <Modal animationType="fade" transparent visible={isVisible} onRequestClose={onClose}>
      <View style={styles.centeredView}>
        <View style={styles.modalView}>
          <Pressable style={styles.closeButton} onPress={onClose}>
            <X size={20} color={C.muted} />
          </Pressable>
          <View style={styles.iconWrap}>
            <LockKeyhole size={28} color={C.cyan} />
          </View>
          <Text style={styles.modalTitle}>{title}</Text>
          <Text style={styles.message}>{message}</Text>

          <TextInput
            value={code}
            onChangeText={setCode}
            placeholder="123456"
            placeholderTextColor={C.muted}
            style={styles.input}
            keyboardType="number-pad"
            maxLength={6}
            editable={!loading}
          />

          <PrimaryButton
            label={loading ? 'Đang xử lý...' : 'Xác nhận'}
            onPress={() => onConfirm(code)}
            disabled={loading || code.length !== 6}
          />
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
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 4,
    elevation: 5,
    width: '90%',
  },
  closeButton: { position: 'absolute', top: S.md, right: S.md, zIndex: 1 },
  iconWrap: {
    alignSelf: 'center',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: C.mintSoft,
    borderRadius: R.pill,
    height: 56,
    width: 56,
    marginBottom: S.md,
  },
  modalTitle: { textAlign: 'center', fontSize: 16, fontWeight: '900', color: C.ink },
  message: { textAlign: 'center', fontSize: 12, fontWeight: '600', color: C.muted, marginTop: S.sm, marginBottom: S.lg },
  input: {
    backgroundColor: C.surface,
    borderColor: C.line,
    borderWidth: 1,
    borderRadius: R.sm,
    padding: S.md,
    marginBottom: S.lg,
    fontSize: 20,
    fontWeight: '900',
    textAlign: 'center',
    letterSpacing: 5,
    color: C.ink,
  },
});
