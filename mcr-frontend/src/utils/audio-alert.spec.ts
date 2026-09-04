import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { closeAlertAudio, playNoSignalAlert } from './audio-alert';

type FakeContext = {
  currentTime: number;
  state: AudioContextState;
  destination: object;
  resume: ReturnType<typeof vi.fn>;
  close: ReturnType<typeof vi.fn>;
  createOscillator: ReturnType<typeof vi.fn>;
  createGain: ReturnType<typeof vi.fn>;
};

let contexts: FakeContext[] = [];
let connectedTo: object[] = [];

function createFakeContext(): FakeContext {
  const destination = { name: 'speakers' };
  const context: FakeContext = {
    currentTime: 0,
    state: 'running',
    destination,
    resume: vi.fn(),
    close: vi.fn(),
    createOscillator: vi.fn(() => ({
      frequency: { value: 0 },
      connect: vi.fn(),
      start: vi.fn(),
      stop: vi.fn(),
    })),
    createGain: vi.fn(() => ({
      gain: {
        setValueAtTime: vi.fn(),
        linearRampToValueAtTime: vi.fn(),
      },
      connect: vi.fn((node: object) => connectedTo.push(node)),
    })),
  };
  contexts.push(context);
  return context;
}

describe('audio alert', () => {
  beforeEach(() => {
    contexts = [];
    connectedTo = [];
    vi.stubGlobal(
      'AudioContext',
      vi.fn(() => createFakeContext()),
    );
  });

  afterEach(() => {
    closeAlertAudio();
    vi.unstubAllGlobals();
  });

  it('sends the beep to the speakers and nowhere else', () => {
    playNoSignalAlert();

    expect(connectedTo.length).toBeGreaterThan(0);
    expect(new Set(connectedTo)).toEqual(new Set([contexts[0]!.destination]));
  });

  it('reuses a single audio context across alerts', () => {
    playNoSignalAlert();
    playNoSignalAlert();

    expect(contexts).toHaveLength(1);
  });

  it('wakes a context the browser suspended', () => {
    playNoSignalAlert();
    contexts[0]!.state = 'suspended';

    playNoSignalAlert();

    expect(contexts[0]!.resume).toHaveBeenCalled();
  });

  it('keeps the recording alive when the beep cannot be played', () => {
    vi.stubGlobal(
      'AudioContext',
      vi.fn(() => {
        throw new Error('no audio output');
      }),
    );

    expect(() => playNoSignalAlert()).not.toThrow();
  });

  it('releases the audio context on close', () => {
    playNoSignalAlert();
    const first = contexts[0]!;

    closeAlertAudio();
    playNoSignalAlert();

    expect(first.close).toHaveBeenCalled();
    expect(contexts).toHaveLength(2);
  });
});
