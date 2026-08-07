import { StyleSheet, Text, type TextProps, type TextStyle } from 'react-native';

import { useFontScale, useHighContrast } from './a11y';

const MUTED_COLOR = '#6E829A';
const HIGH_CONTRAST_COLOR = '#101826';

export function AppText({ style, ...rest }: TextProps) {
  const scale = useFontScale();
  const highContrast = useHighContrast();
  const flat = (StyleSheet.flatten(style) ?? {}) as TextStyle;
  const fontSize = typeof flat.fontSize === 'number' ? flat.fontSize * scale : undefined;
  const color = highContrast && flat.color === MUTED_COLOR ? HIGH_CONTRAST_COLOR : flat.color;
  const fontWeight: TextStyle['fontWeight'] = highContrast ? '900' : flat.fontWeight;

  return <Text {...rest} style={[style, fontSize !== undefined && { fontSize }, { color, fontWeight }]} />;
}
