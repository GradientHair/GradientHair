"use client";

import { useCallback, useRef, useState, useEffect } from "react";
import { useMeetingStore } from "@/store/meeting-store";

export function useWebSocket(meetingId: string) {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const isConnectingRef = useRef(false);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const shouldReconnectRef = useRef(true);
  const lastConnectAttemptRef = useRef(0);
  const lastParticipantsHashRef = useRef<string>("");

  // Use refs for store functions to avoid dependency issues
  const storeRef = useRef(useMeetingStore.getState());
  useEffect(() => {
    storeRef.current = useMeetingStore.getState();
  });

  useEffect(() => {
    lastParticipantsHashRef.current = "";
  }, [meetingId]);

  const sendParticipants = useCallback(() => {
    const ws = wsRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return;
    }

    const participants = storeRef.current.participants || [];
    if (participants.length === 0) {
      return;
    }

    const participantsHash = JSON.stringify(participants);
    if (participantsHash === lastParticipantsHashRef.current) {
      return;
    }
    lastParticipantsHashRef.current = participantsHash;

    ws.send(
      JSON.stringify({
        type: "participants",
        data: participants,
      })
    );
  }, []);

  const connect = useCallback(() => {
    const now = Date.now();
    if (now - lastConnectAttemptRef.current < 500) {
      return;
    }
    lastConnectAttemptRef.current = now;
    // Prevent multiple connection attempts
    if (isConnectingRef.current) {
      console.log("Already connecting, skipping...");
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log("Already connected");
      return;
    }

    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log("Connection in progress...");
      return;
    }

    isConnectingRef.current = true;

    const defaultHost = typeof window !== "undefined" ? window.location.hostname : "localhost";
    const defaultProtocol =
      typeof window !== "undefined" && window.location.protocol === "https:" ? "wss" : "ws";
    const defaultWsUrl = `${defaultProtocol}://${defaultHost}:8000`;
    const wsUrl = process.env.NEXT_PUBLIC_WS_URL || defaultWsUrl;
    const fullUrl = `${wsUrl}/ws/meetings/${encodeURIComponent(meetingId)}`;
    console.log("Connecting to WebSocket:", fullUrl);

    try {
      const ws = new WebSocket(fullUrl);

      ws.onopen = () => {
        console.log("WebSocket connected successfully, readyState:", ws.readyState);
        setIsConnected(true);
        isConnectingRef.current = false;
        reconnectAttemptsRef.current = 0;
        sendParticipants();
      };

      ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          const store = storeRef.current;

          switch (message.type) {
            case "transcript": {
              const data = message.data || {};
              const normalized = {
                ...data,
                latencyMs: data.latencyMs ?? data.latency_ms,
              };
              store.addTranscript(normalized);
              break;
            }
            case "intervention":
              store.addIntervention(message.data);
              break;
            case "speaker_stats":
              store.updateSpeakerStats(message.data.stats);
              break;
            case "stt_status":
              console.log("STT Status:", message.data.status);
              break;
            case "error":
              console.error("Server error:", message.data);
              break;
            default:
              console.log("Unknown message type:", message.type, message);
          }
        } catch (error) {
          console.error("Failed to parse WebSocket message:", error);
        }
      };

      ws.onclose = (event) => {
        console.log("WebSocket closed:", event.code, event.reason);
        setIsConnected(false);
        wsRef.current = null;
        isConnectingRef.current = false;
        if (!shouldReconnectRef.current || event.code === 1000) {
          return;
        }
        const attempt = Math.min(reconnectAttemptsRef.current + 1, 6);
        reconnectAttemptsRef.current = attempt;
        const delay = Math.min(500 * 2 ** (attempt - 1), 8000);
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, delay);
      };

      ws.onerror = () => {
        // Browser doesn't expose error details for security reasons
        console.error("WebSocket connection error occurred, readyState:", ws.readyState);
        isConnectingRef.current = false;
        try {
          ws.close();
        } catch {
          // ignore close errors
        }
      };

      wsRef.current = ws;
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      isConnectingRef.current = false;
    }
  }, [meetingId]);

  useEffect(() => {
    if (isConnected) {
      sendParticipants();
    }
  }, [isConnected, sendParticipants]);

  const disconnect = useCallback(() => {
    shouldReconnectRef.current = false;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      console.log("Disconnecting WebSocket...");
      wsRef.current.close(1000, "Client disconnect");
      wsRef.current = null;
    }
    setIsConnected(false);
    isConnectingRef.current = false;
  }, []);

  const sendAudio = useCallback((audioBase64: string) => {
    const state = wsRef.current?.readyState;
    if (state === WebSocket.OPEN) {
      wsRef.current!.send(
        JSON.stringify({
          type: "audio",
          data: audioBase64,
          timestamp: Date.now(),
        })
      );
    } else {
      // Log when audio can't be sent (only occasionally to avoid spam)
      if (Math.random() < 0.1) {
        console.log("WebSocket not ready, state:", state, "(0=CONNECTING, 1=OPEN, 2=CLOSING, 3=CLOSED)");
      }
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    shouldReconnectRef.current = true;
    return () => {
      shouldReconnectRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmount");
        wsRef.current = null;
      }
    };
  }, []);

  return { connect, disconnect, isConnected, sendAudio };
}
