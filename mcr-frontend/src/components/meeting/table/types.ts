import type { DeliverableDto, MeetingDto } from '@/services/meetings/meetings.types';

export interface MeetingTitleCell {
  name: string;
  id: number;
  creation_date: string;
}

export interface CellMap {
  date: string;
  title: MeetingTitleCell;
  transcription: DeliverableDto[];
  report: DeliverableDto[];
  actions: MeetingDto;
}

export type ColKey = keyof CellMap;
