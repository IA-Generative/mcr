import yup from '@/config/yup';
import type { AddRecordMeetingDto } from '@/services/meetings/meetings.types';
import { t } from '@/plugins/i18n';

type AddRecordMeetingFields = Omit<AddRecordMeetingDto, 'name_platform' | 'creation_date'> & {
  micId: string;
};

export const RecordMeetingSchema: yup.ObjectSchema<AddRecordMeetingFields> = yup.object({
  name: yup.string().required().label(t('meeting.form.fields.name')),
  micId: yup.string().required(),
});

export function recordFieldsToMeetingDto(fields: AddRecordMeetingFields): AddRecordMeetingDto {
  const dto: AddRecordMeetingDto = {
    name: fields.name,
    name_platform: 'MCR_RECORD',
    creation_date: new Date().toISOString(),
  };

  return dto;
}
