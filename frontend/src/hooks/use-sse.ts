'use client';

import { useEffect, useRef } from 'react';

/**
 * Subscribes to a Server-Sent Events endpoint and invokes `onMessage` with
 * each parsed JSON payload. Used instead of polling so the dashboard's
 * live views (job progress, system metrics) update smoothly without
 * repeatedly hammering the REST API.
 */
export function useEventSource<T>(
  url: string | null,
  onMessage: (data: T) => void,
) {
  const onMessageRef = useRef(onMessage);
  onMessageRef.current = onMessage;

  useEffect(() => {
    if (!url) return;

    const source = new EventSource(url);
    source.onmessage = (event: MessageEvent<string>) => {
      try {
        onMessageRef.current(JSON.parse(event.data) as T);
      } catch {
        // ignore malformed frames
      }
    };

    return () => source.close();
  }, [url]);
}
