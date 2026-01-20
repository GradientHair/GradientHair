export class SoundPlayer {
  private audio: HTMLAudioElement | null = null;
  private isReady = false;

  constructor() {
    if (typeof window !== "undefined") {
      this.audio = new Audio("/sounds/alert-chime.wav");
      this.audio.volume = 0.7;
      this.audio.addEventListener("canplaythrough", () => {
        this.isReady = true;
      });
      this.audio.load();
    }
  }

  playAlert() {
    if (this.audio && this.isReady) {
      this.audio.currentTime = 0;
      this.audio.play().catch(console.warn);
    }
  }

  setVolume(volume: number) {
    if (this.audio) {
      this.audio.volume = Math.max(0, Math.min(1, volume));
    }
  }
}

export const soundPlayer = new SoundPlayer();
