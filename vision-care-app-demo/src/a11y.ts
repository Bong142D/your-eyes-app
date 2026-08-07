import { useSyncExternalStore } from 'react';

export const FONT_SIZE_OPTIONS = ['Nhỏ', 'Vừa', 'To'] as const;
export type FontSizeOption = typeof FONT_SIZE_OPTIONS[number];

const FONT_SCALES: Record<FontSizeOption, number> = { 'Nhỏ': 0.88, 'Vừa': 1, 'To': 1.22 };

let fontSizeOption: FontSizeOption = 'Vừa';
let highContrast = false;
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((listener) => listener());
}
function subscribe(onChange: () => void) {
  listeners.add(onChange);
  return () => listeners.delete(onChange);
}

export function setFontSizeOption(option: FontSizeOption) {
  fontSizeOption = option;
  emit();
}
export function setHighContrast(value: boolean) {
  highContrast = value;
  emit();
}

export function useFontSizeOption() {
  return useSyncExternalStore(subscribe, () => fontSizeOption);
}
export function useFontScale() {
  return useSyncExternalStore(subscribe, () => FONT_SCALES[fontSizeOption]);
}
export function useHighContrast() {
  return useSyncExternalStore(subscribe, () => highContrast);
}
