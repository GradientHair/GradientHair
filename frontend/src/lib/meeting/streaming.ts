export type TranscriptSegment = {
  id: string;
  speaker: string;
  role: "host" | "guest" | "bot";
  text: string;
  timestamp: Date;
  isFinal: boolean;
};

export type TranscriptListener = (segment: TranscriptSegment) => void;

export const createTranscriptStreamer = () => {
  const listeners = new Set<TranscriptListener>();

  return {
    onSegment(listener: TranscriptListener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    push(segment: TranscriptSegment) {
      listeners.forEach((listener) => listener(segment));
    },
  };
};
