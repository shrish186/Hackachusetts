import { useEffect, useState } from 'react';
import { getConnState, subscribeConn, type ConnState } from '@/api/client';

/** Subscribe to the API connection state (online / offline / unknown). */
export function useConn(): ConnState {
  const [state, setState] = useState<ConnState>(getConnState());
  useEffect(() => subscribeConn(setState), []);
  return state;
}
