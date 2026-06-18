import { useEffect, useRef } from 'react';

export default function usePolling(fn, intervalMs, active) {
  const fnRef = useRef(fn);
  fnRef.current = fn;

  useEffect(() => {
    if (!active) return;
    fnRef.current();
    const id = setInterval(() => fnRef.current(), intervalMs);
    return () => clearInterval(id);
  }, [active, intervalMs]);
}
