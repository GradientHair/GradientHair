"use client";

import { useCallback, useRef, useState, useEffect } from "react";

/**
 * Audio capture hook that outputs PCM16 format for OpenAI Realtime API
 */
export function useAudioCapture(onAudioData: (base64: string) => void) {
  const audioContextRef = useRef<AudioContext | null>(null);
  const workletNodeRef = useRef<AudioWorkletNode | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const onAudioDataRef = useRef(onAudioData);
  const [isRecording, setIsRecording] = useState(false);
  const bufferRef = useRef<Int16Array[]>([]);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Keep the callback ref up to date
  useEffect(() => {
    onAudioDataRef.current = onAudioData;
  }, [onAudioData]);

  // Convert Float32 samples to Int16 (PCM16)
  const floatTo16BitPCM = (float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return int16Array;
  };

  // Convert Int16Array to base64
  const int16ToBase64 = (int16Array: Int16Array): string => {
    const uint8Array = new Uint8Array(int16Array.buffer);
    let binary = "";
    for (let i = 0; i < uint8Array.length; i++) {
      binary += String.fromCharCode(uint8Array[i]);
    }
    return btoa(binary);
  };

  const start = useCallback(async () => {
    if (isRecording) {
      return;
    }

    try {
      // Get microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 24000, // OpenAI Realtime API expects 24kHz
        },
      });
      streamRef.current = stream;

      // Create AudioContext with 24kHz sample rate (required by OpenAI)
      const audioContext = new AudioContext({ sampleRate: 24000 });
      audioContextRef.current = audioContext;

      // Create source from microphone
      const source = audioContext.createMediaStreamSource(stream);

      // Use ScriptProcessorNode (deprecated but widely supported)
      // Buffer size of 4096 samples at 24kHz = ~170ms chunks
      const processor = audioContext.createScriptProcessor(4096, 1, 1);

      processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        const pcm16 = floatTo16BitPCM(inputData);
        bufferRef.current.push(pcm16);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      // Send accumulated audio every 250ms
      intervalRef.current = setInterval(() => {
        if (bufferRef.current.length > 0) {
          // Concatenate all buffered chunks
          const totalLength = bufferRef.current.reduce((acc, arr) => acc + arr.length, 0);
          const combined = new Int16Array(totalLength);
          let offset = 0;
          for (const chunk of bufferRef.current) {
            combined.set(chunk, offset);
            offset += chunk.length;
          }
          bufferRef.current = [];

          // Convert to base64 and send
          const base64 = int16ToBase64(combined);
          onAudioDataRef.current(base64);
        }
      }, 250);

      setIsRecording(true);
      console.log("Audio capture started (PCM16 @ 24kHz)");
    } catch (error) {
      console.error("Failed to start audio capture:", error);
      throw error;
    }
  }, [isRecording]);

  const stop = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    if (workletNodeRef.current) {
      workletNodeRef.current.disconnect();
      workletNodeRef.current = null;
    }

    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }

    bufferRef.current = [];
    setIsRecording(false);
    console.log("Audio capture stopped");
  }, []);

  const pause = useCallback(() => {
    if (audioContextRef.current?.state === "running") {
      audioContextRef.current.suspend();
    }
  }, []);

  const resume = useCallback(() => {
    if (audioContextRef.current?.state === "suspended") {
      audioContextRef.current.resume();
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  return { start, stop, pause, resume, isRecording };
}
