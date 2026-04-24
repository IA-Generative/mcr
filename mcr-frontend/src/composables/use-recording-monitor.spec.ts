import { describe, it, expect, vi, beforeEach } from 'vitest';
import { useRecordingMonitor, type RecordingMonitorContext } from './use-recording-monitor';

const {
  mockAudioLevelMonitorInstance,
  mockSetTag,
  mockSetContext,
  mockLoggerError,
  mockCaptureMessage,
} = vi.hoisted(() => ({
  mockAudioLevelMonitorInstance: { start: vi.fn(), stop: vi.fn() },
  mockSetTag: vi.fn(),
  mockSetContext: vi.fn(),
  mockLoggerError: vi.fn(),
  mockCaptureMessage: vi.fn(),
}));

vi.mock('@/utils/audio-level-monitor', () => ({
  AudioLevelMonitor: vi.fn().mockImplementation(() => mockAudioLevelMonitorInstance),
}));

vi.mock('@sentry/vue', () => ({
  setTag: (...args: unknown[]) => mockSetTag(...args),
  setContext: (...args: unknown[]) => mockSetContext(...args),
  captureMessage: (...args: unknown[]) => mockCaptureMessage(...args),
  logger: {
    error: (...args: unknown[]) => mockLoggerError(...args),
    fmt: (strings: TemplateStringsArray, ...values: unknown[]) =>
      strings.reduce((acc, str, i) => acc + str + (values[i] ?? ''), ''),
  },
}));

function createMockContext(
  overrides: Partial<RecordingMonitorContext> = {},
): RecordingMonitorContext {
  const track = {
    label: 'Mock Microphone',
    getSettings: () => ({
      deviceId: 'device-1',
      sampleRate: 48000,
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    }),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  };

  const stream = {
    getAudioTracks: () => [track],
  } as unknown as MediaStream;

  const recorder = new EventTarget() as unknown as MediaRecorder;

  return {
    stream,
    recorder,
    meetingId: 42,
    ...overrides,
  };
}

/** Simulate audio level callback calls on the AudioLevelMonitor */
function simulateAudioLevels(levels: number[]) {
  const onLevelUpdate = mockAudioLevelMonitorInstance.start.mock.calls[0]?.[1] as
    | ((level: number) => void)
    | undefined;
  if (!onLevelUpdate) throw new Error('AudioLevelMonitor.start not called yet');
  for (const level of levels) {
    onLevelUpdate(level);
  }
}

describe('useRecordingMonitor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAudioLevelMonitorInstance.start.mockClear();
    mockAudioLevelMonitorInstance.stop.mockClear();
  });

  describe('attach', () => {
    it('should store device settings and clear stats from prior session', () => {
      const { attach, getStats } = useRecordingMonitor();
      const ctx = createMockContext();

      attach(ctx);
      simulateAudioLevels([0.5]);

      // Re-attach resets stats
      attach(createMockContext());
      const stats = getStats();

      expect(stats.maxAudioLevel).toBe(0);
      expect(stats.sampleCount).toBe(0);
      expect(stats.deviceLabel).toBe('Mock Microphone');
      expect(stats.deviceSettings?.deviceId).toBe('device-1');
    });
  });

  describe('detach', () => {
    it('should stop audio level monitor and clear Sentry context', () => {
      const { attach, detach } = useRecordingMonitor();
      attach(createMockContext());

      detach();

      expect(mockAudioLevelMonitorInstance.stop).toHaveBeenCalled();
      expect(mockSetTag).toHaveBeenCalledWith('meeting.id', undefined);
      expect(mockSetContext).toHaveBeenCalledWith('recording', null);
    });

    it('should be idempotent', () => {
      const { attach, detach } = useRecordingMonitor();
      attach(createMockContext());

      detach();
      detach(); // should not throw
    });
  });

  describe('silenceVerdict', () => {
    it('should return isSilent=true when maxAudioLevel < threshold', () => {
      const { attach, silenceVerdict } = useRecordingMonitor();
      attach(createMockContext());

      simulateAudioLevels([0.005, 0.003, 0.002]);

      const { isSilent } = silenceVerdict();
      expect(isSilent).toBe(true);
    });

    it('should return isSilent=true when silenceRatio > 0.98 even with non-zero max', () => {
      const { attach, silenceVerdict } = useRecordingMonitor();
      attach(createMockContext());

      // 99 silent samples + 1 loud sample = silenceRatio 0.99 > 0.98
      const levels = Array(99).fill(0.005).concat([0.5]);
      simulateAudioLevels(levels);

      const { isSilent, stats } = silenceVerdict();
      expect(stats.maxAudioLevel).toBe(0.5);
      expect(stats.silenceRatio).toBeCloseTo(0.99);
      expect(isSilent).toBe(true);
    });

    it('should return isSilent=false for a normal session', () => {
      const { attach, silenceVerdict } = useRecordingMonitor();
      attach(createMockContext());

      simulateAudioLevels([0.3, 0.5, 0.2, 0.4, 0.6]);

      const { isSilent } = silenceVerdict();
      expect(isSilent).toBe(false);
    });
  });

  describe('empty chunk detection', () => {
    it('should invoke onEmptyChunk and increment emptyChunkCount for zero-size blob', () => {
      const onEmptyChunk = vi.fn();
      const { attach, getStats } = useRecordingMonitor({ onEmptyChunk });
      const ctx = createMockContext();
      attach(ctx);

      const event = new Event('dataavailable') as any;
      event.data = new Blob([], { type: 'audio/webm' });
      ctx.recorder.dispatchEvent(event);

      expect(onEmptyChunk).toHaveBeenCalledWith(0);
      expect(getStats().emptyChunkCount).toBe(1);
      expect(mockLoggerError).toHaveBeenCalled();
    });

    it('should NOT invoke onEmptyChunk for non-empty blob', () => {
      const onEmptyChunk = vi.fn();
      const { attach, getStats } = useRecordingMonitor({ onEmptyChunk });
      const ctx = createMockContext();
      attach(ctx);

      const event = new Event('dataavailable') as any;
      event.data = new Blob(['audio-data'], { type: 'audio/webm' });
      ctx.recorder.dispatchEvent(event);

      expect(onEmptyChunk).not.toHaveBeenCalled();
      expect(getStats().emptyChunkCount).toBe(0);
    });
  });

  describe('MediaRecorder error', () => {
    it('should increment recorderErrorEvents and log to Sentry', () => {
      const onRecorderError = vi.fn();
      const { attach, getStats } = useRecordingMonitor({ onRecorderError });
      const ctx = createMockContext();
      attach(ctx);

      const errorEvent = new Event('error');
      ctx.recorder.dispatchEvent(errorEvent);

      expect(getStats().recorderErrorEvents).toBe(1);
      expect(onRecorderError).toHaveBeenCalledWith(errorEvent);
      expect(mockCaptureMessage).toHaveBeenCalledWith(
        expect.stringContaining('MediaRecorder error'),
        expect.objectContaining({
          level: 'error',
          tags: { 'meeting.id': 42 },
        }),
      );
    });
  });

  describe('track mute', () => {
    it('should increment trackMuteEvents', () => {
      const { attach, getStats } = useRecordingMonitor();
      const ctx = createMockContext();
      attach(ctx);

      // Get the mute handler from addEventListener call
      const track = ctx.stream.getAudioTracks()[0];
      const muteCall = (track.addEventListener as ReturnType<typeof vi.fn>).mock.calls.find(
        (call: unknown[]) => call[0] === 'mute',
      );
      expect(muteCall).toBeDefined();

      // Invoke the handler
      muteCall![1]();

      expect(getStats().trackMuteEvents).toBe(1);
    });
  });

  describe('auto-detach on recorder stop', () => {
    it('should stop audio level monitor and clear Sentry context on recorder stop', () => {
      const { attach } = useRecordingMonitor();
      const ctx = createMockContext();
      attach(ctx);

      mockAudioLevelMonitorInstance.stop.mockClear();
      mockSetTag.mockClear();
      mockSetContext.mockClear();

      ctx.recorder.dispatchEvent(new Event('stop'));

      expect(mockAudioLevelMonitorInstance.stop).toHaveBeenCalled();
      expect(mockSetTag).toHaveBeenCalledWith('meeting.id', undefined);
      expect(mockSetContext).toHaveBeenCalledWith('recording', null);
    });
  });

  describe('stats after detach', () => {
    it('should remain readable after detach', () => {
      const { attach, detach, getStats, silenceVerdict } = useRecordingMonitor();
      attach(createMockContext());

      simulateAudioLevels([0.3, 0.5]);
      detach();

      const stats = getStats();
      expect(stats.maxAudioLevel).toBe(0.5);
      expect(stats.sampleCount).toBe(2);

      const verdict = silenceVerdict();
      expect(verdict.isSilent).toBe(false);
      expect(verdict.stats.maxAudioLevel).toBe(0.5);
    });
  });
});
