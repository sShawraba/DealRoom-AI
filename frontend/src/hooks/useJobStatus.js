import { useState } from 'react';
import client from '../api/client';
import usePolling from './usePolling';

const TERMINAL = new Set(['complete', 'failed', 'not_found']);

export default function useJobStatus(jobId, intervalMs = 3000) {
  const [status, setStatus] = useState(null);
  const [done, setDone] = useState(false);

  usePolling(
    async () => {
      if (!jobId) return;
      try {
        const { data } = await client.get(`/jobs/${jobId}/status`);
        setStatus(data);
        if (TERMINAL.has(data.status)) setDone(true);
      } catch {}
    },
    intervalMs,
    !!jobId && !done,
  );

  return { status, done };
}
