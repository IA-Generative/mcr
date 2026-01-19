import type { Nullable } from '@/utils/types';

export const MeetingStatus = [
  'NONE',
  'CAPTURE_PENDING',
  'IMPORT_PENDING',
  'CAPTURE_BOT_IS_CONNECTING',
  'CAPTURE_BOT_CONNECTION_FAILED',
  'CAPTURE_IN_PROGRESS',
  'CAPTURE_DONE',
  'TRANSCRIPTION_PENDING',
  'TRANSCRIPTION_IN_PROGRESS',
  'TRANSCRIPTION_DONE',
  'REPORT_PENDING',
  'REPORT_DONE',
  'CAPTURE_FAILED',
  'TRANSCRIPTION_FAILED',
] as const;
export type MeetingStatus = (typeof MeetingStatus)[number];

export const OnlineMeetingPlatforms = ['COMU', 'WEBINAIRE', 'WEBCONF'] as const;
export const ImportMeetingPlatforms = ['MCR_IMPORT'] as const;
export const RecordMeetingPlatforms = ['MCR_RECORD'] as const;

export type OnlineMeetingPlatforms = (typeof OnlineMeetingPlatforms)[number];
export type ImportMeetingPlatforms = (typeof ImportMeetingPlatforms)[number];
export type RecordMeetingPlatforms = (typeof RecordMeetingPlatforms)[number];

export type AllMeetingPlatforms =
  | OnlineMeetingPlatforms
  | ImportMeetingPlatforms
  | RecordMeetingPlatforms;

type MeetingDtoBase = {
  id: number;
  name: string;
  name_platform: AllMeetingPlatforms;
  status: MeetingStatus;
  creation_date: string;
  start_date: string;
  end_date: string;
};

export interface OnlineMeetingDto extends MeetingDtoBase {
  url: Nullable<string>;
  name_platform: OnlineMeetingPlatforms;
  meeting_password: Nullable<string>;
  meeting_platform_id: Nullable<string>;
}

export interface ImportMeetingDto extends MeetingDtoBase {
  name_platform: ImportMeetingPlatforms;
}

export interface RecordMeetingDto extends MeetingDtoBase {
  name_platform: RecordMeetingPlatforms;
}

export type MeetingDto = OnlineMeetingDto | ImportMeetingDto | RecordMeetingDto;

export type AddOnlineMeetingDto = Omit<
  OnlineMeetingDto,
  'id' | 'status' | 'start_date' | 'end_date'
>;
export type AddImportMeetingDto = Omit<
  ImportMeetingDto,
  'id' | 'status' | 'start_date' | 'end_date'
>;
export type AddRecordMeetingDto = Omit<
  RecordMeetingDto,
  'id' | 'status' | 'start_date' | 'end_date'
>;

export type UpdateOnlineMeetingDto = Partial<AddOnlineMeetingDto>;
export type UpdateImportMeetingDto = Partial<AddImportMeetingDto>;
export type UpdateRecordMeetingDto = Partial<AddRecordMeetingDto>;

export type AddMeetingDto = AddOnlineMeetingDto | AddImportMeetingDto | AddRecordMeetingDto;
export type UpdateMeetingDto =
  | UpdateOnlineMeetingDto
  | UpdateImportMeetingDto
  | UpdateRecordMeetingDto;

export type AddImportMeetingDtoAndFile = {
  dto: AddImportMeetingDto;
  file: File;
};

export type Part = { partNumber: number; etag: string };

// Type guard functions to check the type of meeting DTOs (will validate ImportMeetingDto, AddImportMeetingDto, and UpdateImportMeetingDto)
export function isImportMeeting<T extends { name_platform: string }>(
  meeting: T,
): meeting is T & { name_platform: ImportMeetingDto['name_platform'] } {
  return ImportMeetingPlatforms.includes(meeting.name_platform as any);
}

export function isOnlineMeeting<T extends { name_platform: string }>(
  meeting: T,
): meeting is T & { name_platform: OnlineMeetingDto['name_platform'] } {
  return OnlineMeetingPlatforms.includes(meeting.name_platform as any);
}

export function isRecordMeeting<T extends { name_platform: string }>(
  meeting: T,
): meeting is T & { name_platform: RecordMeetingDto['name_platform'] } {
  return RecordMeetingPlatforms.includes(meeting.name_platform as any);
}

export function isMeetingInProgress(status: MeetingStatus): boolean {
  return (
    status === 'CAPTURE_IN_PROGRESS' ||
    status === 'CAPTURE_PENDING' ||
    status === 'CAPTURE_BOT_IS_CONNECTING'
  );
}

export interface MeetingDtoWithPresignedUrl {
  meeting: MeetingDto;
  presigned_url: string;
}

export function isMeetingFailed(status: MeetingStatus): boolean {
  return (
    status === 'CAPTURE_FAILED' ||
    status === 'TRANSCRIPTION_FAILED' ||
    status === 'CAPTURE_BOT_CONNECTION_FAILED'
  );
}

export interface TranscriptionWaitingTimeResponse {
  estimation_duration_minutes: number;
}
