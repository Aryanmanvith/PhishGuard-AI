import { createContext, useContext } from 'react';

export type ToastKind = 'success' | 'error' | 'info';

export interface ToastApi {
  push: (kind: ToastKind, message: string) => void;
}

export const ToastContext = createContext<ToastApi>({
  // Safe no-op default so components still work in tests without a provider.
  push: () => undefined,
});

export function useToast(): ToastApi {
  return useContext(ToastContext);
}
