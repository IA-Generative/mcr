import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent } from 'vue';
import { render } from '@testing-library/vue';

const { requestMeetingRemovalDuringUnload, pending } = vi.hoisted(() => ({
  requestMeetingRemovalDuringUnload: vi.fn(),
  pending: { meetingIds: [] as number[] },
}));

vi.mock('@/services/meetings/meetings.service', () => ({ requestMeetingRemovalDuringUnload }));
vi.mock('@/composables/use-upload-batch', () => ({
  useUploadBatch: () => ({
    pendingMeetingIds: {
      get value() {
        return pending.meetingIds;
      },
    },
  }),
}));

import { useDiscardImportsOnPageHide } from './use-discard-imports-on-page-hide';

function mountHost() {
  const Host = defineComponent({
    setup() {
      useDiscardImportsOnPageHide();
      return () => null;
    },
  });

  return render(Host);
}

describe('useDiscardImportsOnPageHide', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    pending.meetingIds = [];
  });

  it('gives up the meetings of the imports still running when the page goes away', () => {
    pending.meetingIds = [101, 102];
    mountHost();

    window.dispatchEvent(new Event('pagehide'));

    expect(requestMeetingRemovalDuringUnload).toHaveBeenCalledWith([101, 102]);
  });

  it('asks for nothing when no import is running', () => {
    mountHost();

    window.dispatchEvent(new Event('pagehide'));

    expect(requestMeetingRemovalDuringUnload).not.toHaveBeenCalled();
  });

  it('stops listening once the app is torn down', () => {
    pending.meetingIds = [101];
    const { unmount } = mountHost();

    unmount();
    window.dispatchEvent(new Event('pagehide'));

    expect(requestMeetingRemovalDuringUnload).not.toHaveBeenCalled();
  });
});
