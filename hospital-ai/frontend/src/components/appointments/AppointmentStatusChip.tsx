import type { AppointmentStatus } from '@/types/appointment';
import { STATUS_CHIP_COLORS } from '@/types/appointment';

export default function AppointmentStatusChip({
  status,
}: {
  status: AppointmentStatus;
}) {
  return (
    <span
      className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_CHIP_COLORS[status]}`}
    >
      {status}
    </span>
  );
}
