import yup from '@/config/yup';
import {
  type AddImportMeetingDto,
  type AddImportMeetingDtoAndFile,
} from '@/services/meetings/meetings.types';
import { t } from '@/plugins/i18n';

type AddImportMeetingFields = Omit<
  AddImportMeetingDto,
  'name_platform' | 'creation_date' | 'start_date' | 'end_date'
> & {
  file: File;
};

export const ImportMeetingSchema: yup.ObjectSchema<AddImportMeetingFields> = yup.object({
  name: yup.string().required().label(t('meeting.import-form.fields.name')),
  file: yup.mixed<File>().label(t('meeting.import-form.fields.file.label')).required(),
});

export function importMeetingFieldsToMeetingDto(
  fields: AddImportMeetingFields,
): AddImportMeetingDto {
  return {
    name: fields.name,
    name_platform: 'MCR_IMPORT',
    creation_date: new Date().toISOString(),
  };
}

export function importMeetingFieldsToMeetingDtoAndFile(
  fields: AddImportMeetingFields,
): AddImportMeetingDtoAndFile {
  return {
    dto: importMeetingFieldsToMeetingDto(fields),
    file: fields.file,
  };
}
