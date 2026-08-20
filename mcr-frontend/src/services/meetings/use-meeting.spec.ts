import { renderWithPlugins } from '@/vitest.setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, ref } from 'vue';

const { getAll, removeMany } = vi.hoisted(() => ({ getAll: vi.fn(), removeMany: vi.fn() }));

vi.mock('./meetings.service', () => ({
  getAll,
  removeMany,
  removeOne: vi.fn(),
  getOne: vi.fn(),
  create: vi.fn(),
  update: vi.fn(),
  initCapture: vi.fn(),
  stopCapture: vi.fn(),
  startTranscription: vi.fn(),
  generateMeetingTranscription: vi.fn(),
  generateUploadUrl: vi.fn(),
  uploadFileWithPresignedUrl: vi.fn(),
}));
vi.mock('../lookup/lookup.service', () => ({
  lookupComu: vi.fn(),
  lookupComuByPasscode: vi.fn(),
}));

import { useMeetings } from './use-meeting';

function page(names: string[]) {
  return {
    data: names.map((name, index) => ({ id: index + 1, name })),
    total_pages: 1,
  };
}

function mountMeetings() {
  let query!: ReturnType<ReturnType<typeof useMeetings>['getAllMeetingsQuery']>;
  let deleteMeetings!: ReturnType<ReturnType<typeof useMeetings>['deleteMeetingsMutation']>;

  const Probe = defineComponent({
    setup() {
      const meetings = useMeetings();
      query = meetings.getAllMeetingsQuery({ page: ref(1), pageSize: ref(10) });
      deleteMeetings = meetings.deleteMeetingsMutation();
      return () => null;
    },
  });
  renderWithPlugins(Probe);

  return { query, deleteMeetings };
}

describe('getAllMeetingsQuery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the meetings as of the refresh, not those of the fetch before it', async () => {
    getAll
      .mockResolvedValueOnce(page(['first import']))
      .mockResolvedValueOnce(page(['first import', 'second import']));
    const { query } = mountMeetings();
    await vi.waitFor(() => expect(query.data.value).toBeDefined());

    await query.refetch();

    expect(query.data.value?.data.map((meeting) => meeting.name)).toEqual([
      'first import',
      'second import',
    ]);
  });
});

describe('deleteMeetingsMutation', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAll.mockResolvedValue(page([]));
    removeMany.mockResolvedValue(undefined);
  });

  it('asks for the whole batch with a single request', async () => {
    const { deleteMeetings } = mountMeetings();

    await deleteMeetings.mutateAsync([101, 102, 103]);

    expect(removeMany).toHaveBeenCalledTimes(1);
    expect(removeMany).toHaveBeenCalledWith([101, 102, 103]);
  });

  it('reports a batch the server refused', async () => {
    removeMany.mockRejectedValueOnce(new Error('boom'));
    const { deleteMeetings } = mountMeetings();

    await expect(deleteMeetings.mutateAsync([101, 102, 103])).rejects.toThrow('boom');
  });

  it('refreshes the list only once the deletion has settled', async () => {
    let finishDeletion!: () => void;
    removeMany.mockImplementationOnce(
      () =>
        new Promise<void>((resolve) => {
          finishDeletion = resolve;
        }),
    );
    const { query, deleteMeetings } = mountMeetings();
    await vi.waitFor(() => expect(query.data.value).toBeDefined());
    expect(getAll).toHaveBeenCalledTimes(1);

    const settled = deleteMeetings.mutateAsync([101, 102]).catch(() => undefined);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(getAll).toHaveBeenCalledTimes(1);

    finishDeletion();
    await settled;

    await vi.waitFor(() => expect(getAll).toHaveBeenCalledTimes(2));
  });
});
