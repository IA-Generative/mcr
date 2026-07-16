import { describe, it, expect } from 'vitest';
import { shouldPollDeliverables } from './use-deliverables';
import type { DeliverableDto, DeliverableStatus } from './deliverables.types';

function deliverable(status: DeliverableStatus): DeliverableDto {
  return {
    id: 1,
    meeting_id: 1,
    type: 'TRANSCRIPTION',
    status,
    external_url: null,
    created_at: '2026-07-10T00:00:00Z',
    updated_at: '2026-07-10T00:00:00Z',
  };
}

describe('shouldPollDeliverables', () => {
  it.each(['PENDING', 'IN_PROGRESS'] satisfies DeliverableStatus[])(
    'should_keep_polling_while_a_deliverable_is_%s',
    (status) => {
      expect(shouldPollDeliverables([deliverable('AVAILABLE'), deliverable(status)])).toBe(true);
    },
  );

  it.each(['AVAILABLE', 'FAILED'] satisfies DeliverableStatus[])(
    'should_stop_polling_when_all_deliverables_are_settled_like_%s',
    (status) => {
      expect(shouldPollDeliverables([deliverable(status)])).toBe(false);
    },
  );

  it('should_not_poll_before_the_list_is_loaded', () => {
    expect(shouldPollDeliverables(undefined)).toBe(false);
  });
});
