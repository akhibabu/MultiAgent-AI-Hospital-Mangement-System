import type { Patient } from '@/types/patient';

const CSV_COLUMNS: { key: keyof Patient; header: string }[] = [
  { key: 'patient_number', header: 'Patient Number' },
  { key: 'first_name', header: 'First Name' },
  { key: 'last_name', header: 'Last Name' },
  { key: 'date_of_birth', header: 'Date of Birth' },
  { key: 'gender', header: 'Gender' },
  { key: 'blood_group', header: 'Blood Group' },
  { key: 'phone', header: 'Phone' },
  { key: 'email', header: 'Email' },
  { key: 'city', header: 'City' },
  { key: 'state', header: 'State' },
  { key: 'country', header: 'Country' },
  { key: 'allergies', header: 'Allergies' },
  { key: 'insurance_provider', header: 'Insurance Provider' },
  { key: 'created_at', header: 'Created At' },
];

function escapeCsv(value: unknown): string {
  const raw = value == null ? '' : String(value);
  if (/[",\n]/.test(raw)) {
    return `"${raw.replace(/"/g, '""')}"`;
  }
  return raw;
}

export function exportPatientsToCsv(
  patients: Patient[],
  filename = 'patients.csv',
): void {
  const header = CSV_COLUMNS.map((c) => c.header).join(',');
  const rows = patients.map((patient) =>
    CSV_COLUMNS.map((c) => escapeCsv(patient[c.key])).join(','),
  );
  const csv = [header, ...rows].join('\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
