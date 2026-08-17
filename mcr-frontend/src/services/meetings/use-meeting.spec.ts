import { renderWithPlugins } from '@/vitest.setup';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { defineComponent, ref } from 'vue';

const { getAll } = vi.hoisted(() => ({ getAll: vi.fn() }));

vi.mock('./meetings.service', () => ({
  getAll,
  getOne: vi.fn(),
  create: vi.fn(),
  removeOne: vi.fn(),
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

function mountListQuery() {
  let query!: ReturnType<ReturnType<typeof useMeetings>['getAllMeetingsQuery']>;

  const Probe = defineComponent({
    setup() {
      query = useMeetings().getAllMeetingsQuery({ page: ref(1), pageSize: ref(10) });
      return () => null;
    },
  });
  renderWithPlugins(Probe);

  return query;
}

describe('getAllMeetingsQuery', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('shows the meetings as of the refresh, not those of the fetch before it', async () => {
    getAll
      .mockResolvedValueOnce(page(['first import']))
      .mockResolvedValueOnce(page(['first import', 'second import']));
    const query = mountListQuery();
    await vi.waitFor(() => expect(query.data.value).toBeDefined());

    await query.refetch();

    expect(query.data.value?.data.map((meeting) => meeting.name)).toEqual([
      'first import',
      'second import',
    ]);
  });
});
