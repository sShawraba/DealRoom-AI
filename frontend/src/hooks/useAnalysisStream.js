import { useEffect, useReducer, useRef } from 'react';

const VITE_API_URL = import.meta.env.VITE_API_URL || '/api/v1';

function reducer(state, action) {
  switch (action.type) {
    case 'section_complete':
      return { ...state, sections: [...state.sections, action.payload] };
    case 'analysis.complete':
      return { ...state, done: true };
    case 'analysis.failed':
      return { ...state, error: action.payload, done: true };
    default:
      return state;
  }
}

export default function useAnalysisStream(dealRoomId, reportId, active = true) {
  const [state, dispatch] = useReducer(reducer, { sections: [], done: false, error: null });
  const esRef = useRef(null);

  useEffect(() => {
    if (!active || !dealRoomId || !reportId) return;
    const stored = JSON.parse(localStorage.getItem('dealroom-auth') || '{}');
    const token = stored?.state?.token ?? '';
    const url = `${VITE_API_URL}/deal-rooms/${dealRoomId}/reports/${reportId}/stream?token=${token}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.addEventListener('section_complete', (e) => {
      try { dispatch({ type: 'section_complete', payload: JSON.parse(e.data) }); } catch {}
    });
    es.addEventListener('analysis.complete', () => {
      dispatch({ type: 'analysis.complete' });
      es.close();
    });
    es.addEventListener('analysis.failed', (e) => {
      try { dispatch({ type: 'analysis.failed', payload: JSON.parse(e.data) }); } catch {}
      es.close();
    });

    return () => es.close();
  }, [dealRoomId, reportId, active]);

  return state;
}
