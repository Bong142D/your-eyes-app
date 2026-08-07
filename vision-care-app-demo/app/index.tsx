import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';

import { getToken } from '../src/auth';
import { C, ScreenShell } from '../src/ui';
import { WelcomeScreen } from '../src/YourEyesMockup';

export default function IndexScreen() {
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    getToken().then((token) => {
      if (token) {
        router.replace('/main');
      } else {
        setChecking(false);
      }
    });
  }, []);

  if (checking) {
    return (
      <ScreenShell hideBack>
        <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
          <ActivityIndicator color={C.cyan} />
        </View>
      </ScreenShell>
    );
  }

  return <WelcomeScreen />;
}
