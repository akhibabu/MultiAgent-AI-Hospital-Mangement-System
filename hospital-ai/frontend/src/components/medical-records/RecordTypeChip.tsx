import type { MedicalRecordType } from '@/types/medicalRecord';
import { RECORD_TYPE_COLORS } from '@/types/medicalRecord';

export default function RecordTypeChip({
  type,
}: {
  type: MedicalRecordType;
}) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${RECORD_TYPE_COLORS[type]}`}
    >
      {type}
    </span>
  );
}
