import { Link, useParams } from 'react-router-dom';

import { ErrorBanner, PageHeader, Spinner } from '../components/Feedback';
import ScanResultView from '../components/ScanResultView';
import { useAsync } from '../hooks/useAsync';
import { api } from '../services/api';

export default function ScanDetailPage() {
  const { scanId = '' } = useParams();
  const scan = useAsync(() => api.getScan(scanId), [scanId]);

  return (
    <>
      <PageHeader
        title="Scan details"
        actions={
          <Link to="/history" className="btn-secondary">
            Back to history
          </Link>
        }
      />
      {scan.loading && <Spinner label="Loading scan…" />}
      {scan.error && <ErrorBanner message={scan.error} onRetry={scan.reload} />}
      {scan.data && <ScanResultView scan={scan.data} />}
    </>
  );
}
