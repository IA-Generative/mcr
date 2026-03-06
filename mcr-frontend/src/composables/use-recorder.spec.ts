import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('vue-timer-hook', () => ({
  useStopwatch: () => ({
    seconds: ref(0),
    minutes: ref(0),
    hours: ref(0),
    reset: vi.fn(),
    start: vi.fn(),
    pause: vi.fn(),
  }),
}));

vi.mock('@/utils/audio-level-monitor', () => ({
  AudioLevelMonitor: vi.fn().mockImplementation(() => ({
    start: vi.fn(),
    stop: vi.fn(),
  })),
}));

const mockGetUserMedia = vi.fn();
const mockMediaRecorderStart = vi.fn();

class MockMediaRecorder {
  stream: MediaStream;
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onstop: (() => void) | null = null;
  onstart: (() => void) | null = null;
  onresume: (() => void) | null = null;
  onpause: (() => void) | null = null;

  constructor(stream: MediaStream) {
    this.stream = stream;
  }

  start = mockMediaRecorderStart;
  stop = vi.fn();
  pause = vi.fn();
  resume = vi.fn();
}

vi.stubGlobal('MediaRecorder', MockMediaRecorder);

describe('use-recorder', () => {
  const mockStream = {
    getTracks: () => [{ stop: vi.fn() }],
  } as unknown as MediaStream;

  beforeEach(() => {
    vi.clearAllMocks();
    mockGetUserMedia.mockResolvedValue(mockStream);

    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: mockGetUserMedia, enumerateDevices: vi.fn() },
      writable: true,
      configurable: true,
    });
  });

  it('should pass exact deviceId to getUserMedia when setAudioDeviceId is called', async () => {
    const { useRecorder } = await import('./use-recorder');
    const { setAudioDeviceId, startRecording } = useRecorder();

    setAudioDeviceId('abc123');
    await startRecording();

    expect(mockGetUserMedia).toHaveBeenCalledWith({
      audio: { deviceId: { exact: 'abc123' } },
    });
  });

  it('should throw if no audio device ID is set before recording', async () => {
    // Re-import to get fresh module state
    vi.resetModules();

    // Re-apply mocks after resetModules
    vi.doMock('vue-timer-hook', () => ({
      useStopwatch: () => ({
        seconds: ref(0),
        minutes: ref(0),
        hours: ref(0),
        reset: vi.fn(),
        start: vi.fn(),
        pause: vi.fn(),
      }),
    }));

    vi.doMock('@/utils/audio-level-monitor', () => ({
      AudioLevelMonitor: vi.fn().mockImplementation(() => ({
        start: vi.fn(),
        stop: vi.fn(),
      })),
    }));

    const { useRecorder } = await import('./use-recorder');
    const { startRecording } = useRecorder();

    await expect(startRecording()).rejects.toThrow('Audio device ID must be set before recording');
  });

  describe('getDefaultDeviceId', () => {
    it('should return the preferred device ID (default) when it matches a device', async () => {
      const { useRecorder } = await import('./use-recorder');
      const { getDefaultDeviceId } = useRecorder();

      const devices = [{ deviceId: 'default' }, { deviceId: 'def456' }] as MediaDeviceInfo[];

      expect(getDefaultDeviceId(devices)).toBe('default');
    });

    it('should return the first device ID when preferred ID does not match', async () => {
      const { useRecorder } = await import('./use-recorder');
      const { getDefaultDeviceId } = useRecorder();

      const devices = [{ deviceId: 'abc123' }, { deviceId: 'def456' }] as MediaDeviceInfo[];

      expect(getDefaultDeviceId(devices)).toBe('abc123');
    });

    it('should return empty string when no devices are available', async () => {
      const { useRecorder } = await import('./use-recorder');
      const { getDefaultDeviceId } = useRecorder();

      expect(getDefaultDeviceId([])).toBe('');
    });
  });
});
