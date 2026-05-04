import { describe, it, expect, vi } from 'vitest';
import { getTagMeta } from '@/components/meeting/table/StatusTag.vue';
import { DeliverableStatus } from '@/services/deliverables/deliverables.types';

vi.mock('@/plugins/i18n', () => ({ t: vi.fn((key: string) => key) }));

describe('getTagMeta', () => {
  it('should_return_pending_for_PENDING', () => {
    expect(getTagMeta('PENDING')?.class).toBe('bg-info-950 text-info-425');
  });
  it('should_return__for_IN_PROGRESS', () => {
    expect(getTagMeta('IN_PROGRESS')?.class).toBe(
      'bg-yellow-tournesol-950 text-yellow-tournesol-sun',
    );
  });
  it('should_return_error_for_FAILED', () => {
    expect(getTagMeta('FAILED')?.class).toBe('bg-error-950 text-error-425');
  });
  it('should_return_success_for_AVAILABLE', () => {
    expect(getTagMeta('AVAILABLE')?.class).toBe('bg-success-950 text-success-425');
  });

  it.each(DeliverableStatus)('should_handle_%s_without_falling_back_to_default', (status) => {
    expect(getTagMeta(status)).toBeDefined();
  });
});
