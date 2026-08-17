"use client";

import { createPortal } from "react-dom";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ToastItem } from "./toast-item";
import { ToastContext, type ToastContextValue, type ToastType } from "./use-toast";

const DEFAULT_DURATION = 5000;
const EXIT_DURATION = 220;

function generateId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

type InternalToast = {
  id: string;
  type: ToastType;
  message: string;
  duration: number;
  remainingDuration: number;
  timerId: ReturnType<typeof setTimeout> | null;
  exiting: boolean;
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<InternalToast[]>([]);
  const toastsRef = useRef<InternalToast[]>([]);
  const hoverStartAtRef = useRef<number | null>(null);

  useEffect(() => {
    toastsRef.current = toasts;
  }, [toasts]);

  const remove = useCallback((id: string) => {
    const toast = toastsRef.current.find((t) => t.id === id);
    if (!toast || toast.exiting) return;

    if (toast.timerId) clearTimeout(toast.timerId);

    const next = toastsRef.current.map((t) =>
      t.id === id ? { ...t, timerId: null, exiting: true } : t,
    );
    toastsRef.current = next;
    setToasts(next);

    setTimeout(() => {
      const finalNext = toastsRef.current.filter((t) => t.id !== id);
      toastsRef.current = finalNext;
      setToasts(finalNext);
    }, EXIT_DURATION);
  }, []);

  const schedule = useCallback(
    (id: string, remaining: number) => {
      const timerId = setTimeout(() => {
        remove(id);
      }, remaining);
      const next = toastsRef.current.map((t) =>
        t.id === id ? { ...t, timerId, remainingDuration: remaining } : t,
      );
      toastsRef.current = next;
      setToasts(next);
    },
    [remove],
  );

  const toast = useCallback(
    (type: ToastType, message: string, duration: number = DEFAULT_DURATION): string => {
      const id = generateId();
      const newToast: InternalToast = {
        id,
        type,
        message,
        duration,
        remainingDuration: duration,
        timerId: null,
        exiting: false,
      };
      const next = [...toastsRef.current, newToast];
      toastsRef.current = next;
      setToasts(next);
      if (hoverStartAtRef.current === null) {
        schedule(id, duration);
      }
      return id;
    },
    [schedule],
  );

  const dismiss = useCallback(
    (id: string) => {
      remove(id);
    },
    [remove],
  );

  const handleHoverStart = useCallback(() => {
    if (hoverStartAtRef.current !== null) return;
    hoverStartAtRef.current = Date.now();
    const next = toastsRef.current.map((t) => {
      if (t.timerId) clearTimeout(t.timerId);
      return { ...t, timerId: null };
    });
    toastsRef.current = next;
    setToasts(next);
  }, []);

  const handleHoverEnd = useCallback(() => {
    if (hoverStartAtRef.current === null) return;
    const hoverDuration = Date.now() - hoverStartAtRef.current;
    hoverStartAtRef.current = null;
    const next = toastsRef.current.map((t) => ({
      ...t,
      remainingDuration: Math.max(0, t.remainingDuration - hoverDuration),
      timerId: null,
    }));
    toastsRef.current = next;
    setToasts(next);
    next.forEach((t) => {
      if (t.remainingDuration > 0) {
        schedule(t.id, t.remainingDuration);
      } else {
        remove(t.id);
      }
    });
  }, [schedule, remove]);

  const value = useMemo<ToastContextValue>(
    () => ({
      toasts: toasts.map(({ id, type, message, duration }) => ({
        id,
        type,
        message,
        duration,
      })),
      toast,
      success: (message, duration) => toast("success", message, duration),
      error: (message, duration) => toast("error", message, duration),
      info: (message, duration) => toast("info", message, duration),
      dismiss,
    }),
    [toasts, toast, dismiss],
  );

  const region =
    toasts.length === 0 ? null : (
      <div className="toast-region" role="region" aria-label="Notifications">
        {toasts.map((t) => (
          <ToastItem
            key={t.id}
            toast={{ id: t.id, type: t.type, message: t.message, duration: t.duration }}
            onDismiss={() => dismiss(t.id)}
            onHoverStart={handleHoverStart}
            onHoverEnd={handleHoverEnd}
            exiting={t.exiting}
          />
        ))}
      </div>
    );

  return (
    <ToastContext.Provider value={value}>
      {children}
      {typeof document !== "undefined" ? createPortal(region, document.body) : null}
    </ToastContext.Provider>
  );
}
