import React, { createContext, useState, useCallback } from 'react';
import { Toast, ToastTitle, ToastDescription, ToastClose } from './Toast';

export const ToastContext = createContext(null);

export const ToastProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);

  const addToast = useCallback(({ id, variant = 'default', title, description, duration = 5000 }) => {
    const toastId = id || Date.now().toString();

    setToasts((prevToasts) => {
      // Limit to max 3 visible toasts
      const newToasts = [...prevToasts, { id: toastId, variant, title, description, state: 'open' }];
      return newToasts.slice(-3);
    });

    // Auto-dismiss after duration
    if (duration > 0) {
      setTimeout(() => {
        removeToast(toastId);
      }, duration);
    }

    return toastId;
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prevToasts) =>
      prevToasts.map((toast) =>
        toast.id === id ? { ...toast, state: 'closed' } : toast
      )
    );

    // Remove from DOM after animation completes (300ms as per Toast component)
    setTimeout(() => {
      setToasts((prevToasts) => prevToasts.filter((toast) => toast.id !== id));
    }, 300);
  }, []);

  const toast = useCallback((title, description) => {
    return addToast({ variant: 'default', title, description });
  }, [addToast]);

  const success = useCallback((title, description) => {
    return addToast({ variant: 'success', title, description });
  }, [addToast]);

  const error = useCallback((title, description) => {
    return addToast({ variant: 'error', title, description });
  }, [addToast]);

  const warning = useCallback((title, description) => {
    return addToast({ variant: 'warning', title, description });
  }, [addToast]);

  const info = useCallback((title, description) => {
    return addToast({ variant: 'info', title, description });
  }, [addToast]);

  const value = {
    toast,
    success,
    error,
    warning,
    info,
    addToast,
    removeToast,
  };

  return (
    <ToastContext.Provider value={value}>
      {children}

      {/* Fixed toast container - top-right corner */}
      <div
        className="fixed top-0 right-0 z-50 flex flex-col gap-2 p-4 pointer-events-none"
        style={{ maxWidth: '100vw' }}
      >
        {toasts.map((toastItem) => (
          <Toast
            key={toastItem.id}
            variant={toastItem.variant}
            data-state={toastItem.state}
          >
            <div className="flex-1">
              {toastItem.title && <ToastTitle>{toastItem.title}</ToastTitle>}
              {toastItem.description && (
                <ToastDescription>{toastItem.description}</ToastDescription>
              )}
            </div>
            <ToastClose onClick={() => removeToast(toastItem.id)} />
          </Toast>
        ))}
      </div>
    </ToastContext.Provider>
  );
};
