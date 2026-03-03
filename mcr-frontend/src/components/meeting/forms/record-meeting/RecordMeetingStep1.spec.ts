import { describe, it, expect, vi, beforeEach } from 'vitest';
import { flushPromises } from '@vue/test-utils';

const mockSetAudioDeviceId = vi.fn();
const mockGetAudioInputDevices = vi.fn();

vi.mock('@/composables/use-recorder', () => ({
  useRecorder: () => ({
    getAudioInputDevices: mockGetAudioInputDevices,
    getDefaultDeviceId: (devices: MediaDeviceInfo[], preferredId: string) => {
      const match = devices.find((d) => d.deviceId === preferredId);
      return match ? match.deviceId : (devices[0]?.deviceId ?? '');
    },
    setAudioDeviceId: mockSetAudioDeviceId,
  }),
}));

const mockMicIdRef = ref('default');

vi.mock('vee-validate', () => ({
  useField: (_name: string, _rules: unknown, options?: { initialValue?: string }) => {
    if (_name === 'micId') {
      mockMicIdRef.value = options?.initialValue ?? 'default';
      return { value: mockMicIdRef, errorMessage: ref('') };
    }
    return { value: ref(''), errorMessage: ref('') };
  },
  useIsFormDirty: () => ref(true),
  useIsFormValid: () => ref(true),
}));

function makeDevice(id: string, label: string) {
  return { deviceId: id, label, kind: 'audioinput' } as MediaDeviceInfo;
}

describe('RecordMeetingStep1', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMicIdRef.value = 'default';
  });

  describe('micId auto-correction on mount', () => {
    it("should auto-correct micId to first device when 'default' doesn't match any device", async () => {
      mockGetAudioInputDevices.mockResolvedValue([
        makeDevice('abc123', 'Mic 1'),
        makeDevice('def456', 'Mic 2'),
      ]);

      const { renderWithPlugins } = await import('@/vitest.setup');
      const RecordMeetingStep1 = (await import('./RecordMeetingStep1.vue')).default;

      renderWithPlugins(RecordMeetingStep1);
      await flushPromises();

      expect(mockMicIdRef.value).toBe('abc123');
    });

    it('should keep micId unchanged when it matches a loaded device', async () => {
      mockMicIdRef.value = 'abc123';
      mockGetAudioInputDevices.mockResolvedValue([
        makeDevice('abc123', 'Mic 1'),
        makeDevice('def456', 'Mic 2'),
      ]);

      const { renderWithPlugins } = await import('@/vitest.setup');
      const RecordMeetingStep1 = (await import('./RecordMeetingStep1.vue')).default;

      renderWithPlugins(RecordMeetingStep1);
      await flushPromises();

      expect(mockMicIdRef.value).toBe('abc123');
    });
  });

  describe('setAudioDeviceId on next step', () => {
    it('should call setAudioDeviceId with the auto-selected first device ID when clicking Next', async () => {
      mockGetAudioInputDevices.mockResolvedValue([
        makeDevice('abc123', 'Mic 1'),
        makeDevice('def456', 'Mic 2'),
      ]);

      const { screen } = await import('@testing-library/vue');
      const userEvent = (await import('@testing-library/user-event')).default;
      const { renderWithPlugins } = await import('@/vitest.setup');
      const RecordMeetingStep1 = (await import('./RecordMeetingStep1.vue')).default;

      renderWithPlugins(RecordMeetingStep1);
      await flushPromises();

      const nextButton = screen.getByText('Suivant');
      await userEvent.click(nextButton);

      expect(mockSetAudioDeviceId).toHaveBeenCalledWith('abc123');
    });

    it('should call setAudioDeviceId with the manually selected device ID when clicking Next', async () => {
      mockGetAudioInputDevices.mockResolvedValue([
        makeDevice('abc123', 'Mic 1'),
        makeDevice('def456', 'Mic 2'),
      ]);

      const { screen } = await import('@testing-library/vue');
      const userEvent = (await import('@testing-library/user-event')).default;
      const { renderWithPlugins } = await import('@/vitest.setup');
      const RecordMeetingStep1 = (await import('./RecordMeetingStep1.vue')).default;

      renderWithPlugins(RecordMeetingStep1);
      await flushPromises();

      // Simulate user changing the device selection
      mockMicIdRef.value = 'def456';

      const nextButton = screen.getByText('Suivant');
      await userEvent.click(nextButton);

      expect(mockSetAudioDeviceId).toHaveBeenCalledWith('def456');
    });
  });
});
