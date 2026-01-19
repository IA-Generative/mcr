import {
  AUDIO_SAMPLE_MIDPOINT,
  DECAY_RATE,
  FFT_SIZE,
  GAIN,
  SMOOTHING_TIME_CONSTANT,
} from '@/config/audioMonitor';
import { useRafFn } from '@vueuse/core';

interface AudioLevelMonitorConfig {
  fftSize?: number;
  smoothingTimeConstant?: number;
  decayRate?: number;
  gain?: number;
}

export class AudioLevelMonitor {
  private audioContext: AudioContext | undefined;
  private mediaStreamSourceNode: MediaStreamAudioSourceNode | undefined;
  private analyserNode: AnalyserNode | undefined;
  private animationFrameRequestId: number | undefined;
  private currentLevel: number = 0;

  private readonly config: Required<AudioLevelMonitorConfig>;

  constructor(config: AudioLevelMonitorConfig = {}) {
    this.config = {
      fftSize: config.fftSize ?? FFT_SIZE,
      smoothingTimeConstant: config.smoothingTimeConstant ?? SMOOTHING_TIME_CONSTANT,
      decayRate: config.decayRate ?? DECAY_RATE,
      gain: config.gain ?? GAIN,
    };
  }

  start(mediaStream: MediaStream, onLevelUpdate: (level: number) => void): void {
    this.stop();

    // Create the audio context (compatible with webkit for Safari).
    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();

    this.mediaStreamSourceNode = this.audioContext.createMediaStreamSource(mediaStream);

    // Create and configure the analyzer.
    this.analyserNode = this.audioContext.createAnalyser();
    this.analyserNode.fftSize = this.config.fftSize;
    this.analyserNode.smoothingTimeConstant = this.config.smoothingTimeConstant;

    // Connect the source to the analyzer.
    this.mediaStreamSourceNode.connect(this.analyserNode);

    // Buffer to store the audio samples in the time domain.
    const timeDomainBuffer = new Uint8Array(this.analyserNode.fftSize);

    // Recursive function to update the audio level.
    const updateLevel = useRafFn(() => {
      if (!this.analyserNode) return;

      this.analyserNode.getByteTimeDomainData(timeDomainBuffer);

      this.currentLevel = Math.min(
        1,
        Math.max(0, this.calculateSmoothedLevel(this.calculateRootMeanSquare(timeDomainBuffer))),
      );

      onLevelUpdate(this.currentLevel);
    });

    updateLevel.resume();
  }

  calculateRootMeanSquare(timeDomainBuffer: Uint8Array): number {
    // Normalize samples between -1 and 1, then sum their squares.
    const sumSquares = timeDomainBuffer.reduce((accumulator, sample) => {
      const centeredSample = (sample - AUDIO_SAMPLE_MIDPOINT) / AUDIO_SAMPLE_MIDPOINT;
      return accumulator + Math.pow(centeredSample, 2);
    }, 0);
    return Math.sqrt(sumSquares / timeDomainBuffer.length);
  }

  calculateSmoothedLevel(rootMeanSquare: number): number {
    return Math.max(rootMeanSquare * this.config.gain, this.currentLevel - this.config.decayRate);
  }

  stop(): void {
    if (this.animationFrameRequestId !== undefined) {
      cancelAnimationFrame(this.animationFrameRequestId);
      this.animationFrameRequestId = undefined;
    }

    try {
      if (this.mediaStreamSourceNode) {
        this.mediaStreamSourceNode.disconnect();
        this.mediaStreamSourceNode = undefined;
      }

      if (this.analyserNode) {
        this.analyserNode.disconnect();
        this.analyserNode = undefined;
      }

      if (this.audioContext) {
        this.audioContext.close();
        this.audioContext = undefined;
      }
    } catch (_error) {
      // Ignore the cleanup errors.
    }

    this.currentLevel = 0;
  }

  getCurrentLevel(): number {
    return this.currentLevel;
  }
}

export function createAudioLevelMonitor(
  mediaStream: MediaStream,
  onLevelUpdate: (level: number) => void,
  config?: AudioLevelMonitorConfig,
): () => void {
  const monitor = new AudioLevelMonitor(config);
  monitor.start(mediaStream, onLevelUpdate);

  return () => monitor.stop();
}
