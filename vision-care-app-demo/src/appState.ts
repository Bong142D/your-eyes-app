import { useSyncExternalStore } from 'react';

let isLinked = false;
const listeners = new Set<() => void>();

export function setIsLinked(value: boolean) {
  isLinked = value;
  listeners.forEach((listener) => listener());
}

export function useIsLinked() {
  return useSyncExternalStore(
    (onChange) => { listeners.add(onChange); return () => listeners.delete(onChange); },
    () => isLinked,
  );
}
