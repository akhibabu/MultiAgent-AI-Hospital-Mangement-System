import { Link, useParams } from 'react-router-dom';
import ErrorBoundary from '@/components/common/ErrorBoundary';
import DocumentViewer from '@/components/medical-records/DocumentViewer';
import Loading from '@/components/ui/Loading';
import ErrorState from '@/components/ui/ErrorState';
import {
  useDeleteMedicalDocument,
  useMedicalDocument,
  useMedicalRecord,
} from '@/hooks/useMedicalRecords';

export default function DocumentViewerPage() {
  const { documentId } = useParams();
  const {
    data: document,
    isLoading,
    isError,
    error,
    refetch,
  } = useMedicalDocument(documentId);
  const recordQuery = useMedicalRecord(document?.medical_record_id);
  const deleteMutation = useDeleteMedicalDocument(document?.medical_record_id);

  if (isLoading) return <Loading message="Loading document…" />;
  if (isError || !document) {
    return (
      <ErrorState
        title="Unable to load document"
        message={error instanceof Error ? error.message : 'Not found'}
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <ErrorBoundary title="Document viewer error">
      <section className="mx-auto max-w-5xl space-y-4">
        <div className="flex justify-end">
          <Link
            to={`/medical-records/${document.medical_record_id}`}
            className="rounded-lg border border-[var(--border-color)] px-4 py-2 text-sm"
          >
            Back to record
          </Link>
        </div>
        <DocumentViewer
          document={document}
          record={recordQuery.data}
          onDelete={async () => {
            await deleteMutation.mutateAsync(document.id);
            window.history.back();
          }}
        />
      </section>
    </ErrorBoundary>
  );
}
