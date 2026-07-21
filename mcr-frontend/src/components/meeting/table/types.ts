import type { MeetingDto } from '@/services/meetings/meetings.types';
import type { DeliverableStatus } from '@/services/deliverables/deliverables.types';

export interface MeetingTitleCell {
  name: string;
  id: number;
  creation_date: string;
}

export interface CellMap {
  date: string;
  title: MeetingTitleCell;
  transcription: DeliverableStatus | null;
  report: DeliverableStatus | null;
  actions: MeetingDto;
}

export type ColKey = keyof CellMap;
