import React, { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react';
import { WebSocketLiveEvent, LiveProviderStatus } from '@/types/api';
import { api } from '@/api/client';

export type ConnectionStatus = 'connected' | 'connecting' | 'disconnected' | 'reconnecting';

interface WebSocketContextType {
  connectionStatus: ConnectionStatus;
  providerStatus: LiveProviderStatus | null;
  liveTransactions: any[];
  lastEventTime: string | null;
  lastMessage: WebSocketLiveEvent | null;
  subscribeToCase: (caseId: string) => void;
  unsubscribeFromCase: (caseId: string) => void;
  registerListener: (type: string, handler: (event: WebSocketLiveEvent) => void) => () => void;
  refreshStatus: () => Promise<void>;
}

const WebSocketContext = createContext<WebSocketContextType | null>(null);

function getWebSocketUrl(): string {
  if (typeof window !== 'undefined') {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    if (import.meta.env.DEV) {
      return `${protocol}//${window.location.host}/ws/live`;
    }
    const apiBase = import.meta.env.VITE_API_BASE_URL;
    if (apiBase) {
      try {
        const url = new URL(apiBase, window.location.origin);
        const wsProto = url.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${wsProto}//${url.host}/ws/live`;
      } catch {
        // Fall back to window host
      }
    }
    return `${protocol}//${window.location.host}/ws/live`;
  }
  return 'ws://localhost:8000/ws/live';
}

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('connecting');
  const [providerStatus, setProviderStatus] = useState<LiveProviderStatus | null>(null);
  const [liveTransactions, setLiveTransactions] = useState<any[]>([]);
  const [lastEventTime, setLastEventTime] = useState<string | null>(null);
  const [lastMessage, setLastMessage] = useState<WebSocketLiveEvent | null>(null);

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<any>(null);
  const pingIntervalRef = useRef<any>(null);
  const backoffRef = useRef(1000);
  const listenersRef = useRef<Map<string, Set<(event: WebSocketLiveEvent) => void>>>(new Map());
  const subscribedCasesRef = useRef<Set<string>>(new Set());

  const refreshStatus = useCallback(async () => {
    try {
      const live = await api.getLiveStatus();
      setProviderStatus(live.provider);
      if (live.provider.last_event_time) {
        setLastEventTime(live.provider.last_event_time);
      }
    } catch {
      // Handled silently
    }
  }, []);

  const registerListener = useCallback((type: string, handler: (event: WebSocketLiveEvent) => void) => {
    if (!listenersRef.current.has(type)) {
      listenersRef.current.set(type, new Set());
    }
    listenersRef.current.get(type)!.add(handler);
    return () => {
      listenersRef.current.get(type)?.delete(handler);
    };
  }, []);

  const subscribeToCase = useCallback((caseId: string) => {
    subscribedCasesRef.current.add(caseId);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'subscribe', case_id: caseId }));
    }
  }, []);

  const unsubscribeFromCase = useCallback((caseId: string) => {
    subscribedCasesRef.current.delete(caseId);
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'unsubscribe', case_id: caseId }));
    }
  }, []);

  const connect = useCallback(() => {
    if (socketRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = getWebSocketUrl();
    try {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        setConnectionStatus('connected');
        backoffRef.current = 1000;

        // Re-subscribe to any active cases
        subscribedCasesRef.current.forEach((caseId) => {
          ws.send(JSON.stringify({ type: 'subscribe', case_id: caseId }));
        });

        // Start 15s heartbeats
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping', timestamp: Date.now() }));
          }
        }, 15000);

        refreshStatus();
      };

      ws.onmessage = (event) => {
        try {
          const msg: WebSocketLiveEvent = JSON.parse(event.data);
          setLastMessage(msg);

          if (msg.timestamp) {
            setLastEventTime(msg.timestamp);
          }

          if (msg.type === 'transaction.new' && msg.data) {
            setLiveTransactions((prev) => {
              // Deduplicate by tx_hash or event_id
              const id = msg.data.event_id || msg.data.tx_hash;
              if (prev.some((p) => (p.event_id || p.tx_hash) === id)) {
                return prev;
              }
              return [msg.data, ...prev].slice(0, 50);
            });
          }

          // Dispatch to registered event listeners
          const handlers = listenersRef.current.get(msg.type);
          if (handlers) {
            handlers.forEach((h) => {
              try {
                h(msg);
              } catch (err) {
                console.error('Error in event handler:', err);
              }
            });
          }
        } catch {
          // ignore parsing error
        }
      };

      ws.onclose = () => {
        clearInterval(pingIntervalRef.current);
        setConnectionStatus('reconnecting');
        const delay = Math.min(30000, backoffRef.current);
        backoffRef.current = Math.min(30000, backoffRef.current * 1.5);
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      setConnectionStatus('disconnected');
    }
  }, [refreshStatus]);

  useEffect(() => {
    refreshStatus();
    connect();

    return () => {
      clearInterval(pingIntervalRef.current);
      clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [connect, refreshStatus]);

  return (
    <WebSocketContext.Provider
      value={{
        connectionStatus,
        providerStatus,
        liveTransactions,
        lastEventTime,
        lastMessage,
        subscribeToCase,
        unsubscribeFromCase,
        registerListener,
        refreshStatus,
      }}
    >
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
