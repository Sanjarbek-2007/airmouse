import { useCallback, useEffect, useState } from 'react';
import { AppState } from 'react-native';
import { AirCursor, IDLE_STATUS, Status } from '../native/AirCursor';

/** Live engine state (10 Hz push) merged with slowly-changing setup status (permissions...). */
export function useAirCursor() {
  const [status, setStatus] = useState<Status>(IDLE_STATUS);

  const refresh = useCallback(async () => {
    try { setStatus(await AirCursor.getStatus()); } catch { /* native not ready yet */ }
  }, []);

  useEffect(() => {
    refresh();
    const poll = setInterval(refresh, 1500);
    const app = AppState.addEventListener('change', s => { if (s === 'active') { refresh(); } });
    const off = AirCursor.onState(s => setStatus(prev => ({ ...prev, ...s })));
    return () => { clearInterval(poll); app.remove(); off(); };
  }, [refresh]);

  return { status, refresh };
}
