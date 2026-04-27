import { describe, it, expect, vi, beforeAll, afterAll } from 'vitest';
import { screen } from '@testing-library/vue';
import MeetingFrontMatterV2 from './MeetingFrontMatterV2.vue';
import { renderWithPlugins } from '@/vitest.setup';
import type { MeetingDetailDto } from '@/services/meetings/meetings.types';

vi.mock('@gouvminint/vue-dsfr', () => ({
  DsfrBreadcrumb: { template: '<nav />' },
}));

const originalTZ = process.env.TZ;
beforeAll(() => {
  process.env.TZ = 'Europe/Paris';
});
afterAll(() => {
  process.env.TZ = originalTZ;
});

function makeMeeting(namePlatform: string): MeetingDetailDto {
  return {
    id: 1,
    name: 'Réunion test',
    name_platform: namePlatform,
    status: 'NONE',
    creation_date: '2025-03-15T14:30:00Z',
    start_date: '2025-03-15T14:30:00Z',
    end_date: '2025-03-15T15:30:00Z',
    url: null,
    meeting_password: null,
    meeting_platform_id: null,
    deliverables: [],
  } as MeetingDetailDto;
}

describe('MeetingFrontMatterV2 - getSubtitleFromPlatformName', () => {
  it('should display import subtitle for MCR_IMPORT', () => {
    renderWithPlugins(MeetingFrontMatterV2, {
      props: { meeting: makeMeeting('MCR_IMPORT') },
    });
    expect(screen.getByText('Fichier importé le')).toBeInTheDocument();
  });

  it('should display record subtitle for MCR_RECORD', () => {
    renderWithPlugins(MeetingFrontMatterV2, {
      props: { meeting: makeMeeting('MCR_RECORD') },
    });
    expect(screen.getByText('Réunion en présentiel enregistrée le')).toBeInTheDocument();
  });

  it('should display visio subtitle with platform name for VISIO', () => {
    renderWithPlugins(MeetingFrontMatterV2, {
      props: { meeting: makeMeeting('VISIO') },
    });
    expect(screen.getByText('Enregistré avec VISIO le')).toBeInTheDocument();
  });

  it('should display visio subtitle with platform name for WEBEX', () => {
    renderWithPlugins(MeetingFrontMatterV2, {
      props: { meeting: makeMeeting('WEBEX') },
    });
    expect(screen.getByText('Enregistré avec WEBEX le')).toBeInTheDocument();
  });
});
