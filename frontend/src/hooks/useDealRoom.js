import { useState, useEffect, useCallback } from 'react';
import * as dealRoomsApi from '../api/dealRooms';
import * as documentsApi from '../api/documents';

export default function useDealRoom(dealRoomId) {
  const [dealRoom, setDealRoom] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [members, setMembers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!dealRoomId) return;
    try {
      const [dr, docs, mems] = await Promise.all([
        dealRoomsApi.get(dealRoomId),
        documentsApi.list(dealRoomId, { page: 1, page_size: 100 }),
        dealRoomsApi.listMembers(dealRoomId),
      ]);
      setDealRoom(dr);
      setDocuments(docs.items ?? []);
      setMembers(mems?.items ?? []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [dealRoomId]);

  useEffect(() => {
    fetch();
    const interval = setInterval(fetch, 4000);
    return () => clearInterval(interval);
  }, [fetch]);

  return { dealRoom, documents, members, loading, error, refetch: fetch };
}
