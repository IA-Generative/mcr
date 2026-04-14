import type { MeetingDto } from '@/services/meetings/meetings.types';

export interface MeetingTitleCell {
  name: string;
  id: number;
}

export interface CellMap {
  date: string;
  title: MeetingTitleCell;
  transcription: string;
  report: string;
  actions: MeetingDto;
}

export type ColKey = keyof CellMap;
