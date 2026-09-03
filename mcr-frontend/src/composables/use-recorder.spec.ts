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

const { mockGetUserMedia } = vi.hoisted(() => ({
  mockGetUserMedia: vi.fn(),
}));

type MockTrack = MediaStreamTrack & { stop: ReturnType<typeof vi.fn> };
type MockStream = MediaStream & { id: string };

type MockNode = {
  stream?: MockStream;
  connect: ReturnType<typeof vi.fn>;
  disconnect: ReturnType<typeof vi.fn>;
};

type MockSourceNode = MockNode & { of: MockStream };

const graph = {
  initialState: 'running' as AudioContextState,
  contexts: [] as MockAudioContext[],
  sources: [] as MockSourceNode[],
  destinations: [] as MockNode[],
  destinationArgs: [] as unknown[][],
  recorders: [] as MockMediaRecorder[],
  // Ordered trace of the calls whose sequence is part of the contract.
  trace: [] as string[],
};

function makeStream(id: string): MockStream {
  const track = {
    id,
    label: id,
    stop: vi.fn(),
    getSettings: () => ({ deviceId: id }),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  } as unknown as MockTrack;
  return {
    id,
    getTracks: () => [track],
    getAudioTracks: () => [track],
  } as unknown as MockStream;
}

function trackOf(stream: MockStream): MockTrack {
  return stream.getTracks()[0] as MockTrack;
}

class MockAudioContext {
  state: AudioContextState = graph.initialState;

  constructor() {
    graph.contexts.push(this);
  }

  resume = vi.fn(async () => {
    graph.trace.push('resume');
    this.state = 'running';
  });

  close = vi.fn(async () => {
    graph.trace.push('close');
    this.state = 'closed';
  });

  createMediaStreamDestination = vi.fn((...args: unknown[]): MockNode => {
    graph.destinationArgs.push(args);
    const node: MockNode = {
      stream: makeStream(`destination-${graph.destinations.length}`),
      connect: vi.fn(),
      disconnect: vi.fn(),
    };
    graph.destinations.push(node);
    return node;
  });

  createMediaStreamSource = vi.fn((stream: MockStream): MockSourceNode => {
    const node: MockSourceNode = {
      of: stream,
      connect: vi.fn(() => graph.trace.push(`connect:${stream.id}`)),
      disconnect: vi.fn(() => graph.trace.push(`disconnect:${stream.id}`)),
    };
    graph.sources.push(node);
    return node;
  });
}

class MockMediaRecorder {
  stream: MediaStream;
  state: MediaRecorderState = 'recording';
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onstop: (() => void) | null = null;
  onstart: (() => void) | null = null;
  onresume: (() => void) | null = null;
  onpause: (() => void) | null = null;

  start = vi.fn();
  stop = vi.fn();
  pause = vi.fn();
  resume = vi.fn();

  constructor(stream: MediaStream) {
    this.stream = stream;
    graph.recorders.push(this);
    graph.trace.push('new MediaRecorder');
  }
}

vi.stubGlobal('MediaRecorder', MockMediaRecorder);
vi.stubGlobal('AudioContext', MockAudioContext);

describe('use-recorder', () => {
  let micA: MockStream;

  async function importRecorder() {
    const { useRecorder } = await import('./use-recorder');
    return useRecorder();
  }

  async function startOnDevice(deviceId: string, options = {}) {
    const recorder = await importRecorder();
    recorder.setAudioDeviceId(deviceId);
    await recorder.startRecording(options);
    return recorder;
  }

  beforeEach(async () => {
    vi.clearAllMocks();
    await vi.resetModules();

    graph.initialState = 'running';
    graph.contexts = [];
    graph.sources = [];
    graph.destinations = [];
    graph.destinationArgs = [];
    graph.recorders = [];
    graph.trace = [];

    micA = makeStream('mic-a');
    mockGetUserMedia.mockResolvedValue(micA);

    Object.defineProperty(navigator, 'mediaDevices', {
      value: {
        getUserMedia: mockGetUserMedia,
        enumerateDevices: vi.fn().mockResolvedValue([]),
      },
      writable: true,
      configurable: true,
    });
  });

  it('should pass the device and disable echo cancellation / noise suppression to getUserMedia', async () => {
    await startOnDevice('abc123');

    // Echo cancellation would subtract meeting audio played through the speakers
    // and noise suppression would gate distant speech, silencing the recording.
    expect(mockGetUserMedia).toHaveBeenCalledWith({
      audio: {
        deviceId: { ideal: 'abc123' },
        echoCancellation: false,
        noiseSuppression: false,
      },
    });
  });

  describe('listAudioInputDevices', () => {
    it('should list only the audio inputs the browser exposes', async () => {
      const { listAudioInputDevices } = await importRecorder();

      navigator.mediaDevices.enumerateDevices = vi.fn().mockResolvedValue([
        { deviceId: 'mic-1', label: 'Micro intégré', groupId: 'g1', kind: 'audioinput' },
        { deviceId: 'cam-1', label: 'Webcam', groupId: 'g2', kind: 'videoinput' },
      ]);

      expect(await listAudioInputDevices()).toEqual([
        { deviceId: 'mic-1', label: 'Micro intégré', groupId: 'g1' },
      ]);
    });

    it('should not ask for the microphone permission', async () => {
      const { listAudioInputDevices } = await importRecorder();

      navigator.mediaDevices.enumerateDevices = vi.fn().mockResolvedValue([]);

      await listAudioInputDevices();

      expect(mockGetUserMedia).not.toHaveBeenCalled();
    });

    it('should return an empty list when the devices cannot be enumerated', async () => {
      const { listAudioInputDevices } = await importRecorder();

      navigator.mediaDevices.enumerateDevices = vi.fn().mockRejectedValue(new Error('denied'));

      expect(await listAudioInputDevices()).toEqual([]);
    });
  });

  it('should expose the device the recording is running on', async () => {
    const { setAudioDeviceId, currentAudioId } = await importRecorder();

    setAudioDeviceId('mic-1');

    expect(currentAudioId.value).toBe('mic-1');
  });

  describe('getDefaultDeviceId', () => {
    it('should return the preferred device ID (default) when it matches a device', async () => {
      const { getDefaultDeviceId } = await importRecorder();

      const devices = [{ deviceId: 'default' }, { deviceId: 'def456' }] as MediaDeviceInfo[];

      expect(getDefaultDeviceId(devices)).toBe('default');
    });

    it('should return the first device ID when preferred ID does not match', async () => {
      const { getDefaultDeviceId } = await importRecorder();

      const devices = [{ deviceId: 'abc123' }, { deviceId: 'def456' }] as MediaDeviceInfo[];

      expect(getDefaultDeviceId(devices)).toBe('abc123');
    });

    it('should return empty string when no devices are available', async () => {
      const { getDefaultDeviceId } = await importRecorder();

      expect(getDefaultDeviceId([])).toBe('');
    });
  });

  describe('audio graph', () => {
    it('should record the destination of the graph, never the microphone stream itself', async () => {
      // The recorder must be wired to a stream that survives a device change.
      await startOnDevice('mic-a');

      expect(graph.recorders).toHaveLength(1);
      expect(graph.recorders[0].stream).toBe(graph.destinations[0].stream);
      expect(graph.recorders[0].stream).not.toBe(micA);
      expect(graph.sources[0].of).toBe(micA);
      expect(graph.sources[0].connect).toHaveBeenCalledWith(graph.destinations[0]);
    });

    it('should split the recording into one-minute chunks from a single start', async () => {
      await startOnDevice('mic-a');

      expect(graph.recorders[0].start).toHaveBeenCalledTimes(1);
      expect(graph.recorders[0].start).toHaveBeenCalledWith(60_000);
    });

    it('should resume a suspended context before wiring the recorder to it', async () => {
      graph.initialState = 'suspended';

      await startOnDevice('mic-a');

      expect(graph.contexts[0].resume).toHaveBeenCalled();
      expect(graph.trace.indexOf('resume')).toBeLessThan(graph.trace.indexOf('new MediaRecorder'));
    });

    it('should leave the channel layout of the destination untouched', async () => {
      // Down-mixing to mono would destroy a phase-inverted stereo signal before the
      // backend can repair it.
      await startOnDevice('mic-a');

      expect(graph.destinationArgs).toEqual([[]]);
    });

    it('should release the microphone when the recording stops', async () => {
      // Stopping the recorder's own (synthetic) stream would leave the device held
      // and the OS recording indicator on.
      const { stopRecording } = await startOnDevice('mic-a');

      stopRecording();

      expect(trackOf(micA).stop).toHaveBeenCalled();
      expect(graph.contexts[0].close).toHaveBeenCalled();
    });

    it('should release the microphone when the recording is aborted', async () => {
      const { abortRecording } = await startOnDevice('mic-a');

      abortRecording();

      expect(trackOf(micA).stop).toHaveBeenCalled();
      expect(graph.contexts[0].close).toHaveBeenCalled();
    });

    it('should hand the monitor the recorded stream and the microphone track', async () => {
      const onRecordingStart = vi.fn();

      await startOnDevice('mic-a', { onRecordingStart });

      expect(onRecordingStart).toHaveBeenCalledWith(
        expect.objectContaining({
          stream: graph.destinations[0].stream,
          micTrack: trackOf(micA),
        }),
      );
    });
  });
});
