export const DeliverableStatus = [
  'REQUESTED',
  'PENDING',
  'IN_PROGRESS',
  'AVAILABLE',
  'FAILED',
] as const;
export type DeliverableStatus = (typeof DeliverableStatus)[number];

export const DeliverableType = [
  'TRANSCRIPTION',
  'DECISION_RECORD',
  'DETAILED_SYNTHESIS',
  'CUSTOM_REPORT',
] as const;
export type DeliverableType = (typeof DeliverableType)[number];

export interface DeliverableDto {
  id: number;
  meeting_id: number;
  type: DeliverableType;
  status: DeliverableStatus;
  external_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface DeliverableListResponse {
  deliverables: DeliverableDto[];
}

export interface DeliverableCreateRequest {
  meeting_id: number;
  type: DeliverableType;
  custom_prompt?: string;
}
