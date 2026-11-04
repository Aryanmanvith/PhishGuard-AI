import { Link } from 'react-router-dom';

import { EmptyState } from '../components/Feedback';

export default function NotFoundPage() {
  return (
    <div className="card">
      <EmptyState icon="alert" title="Page not found">
        That page does not exist.
        <div className="mt-4">
          <Link to="/" className="btn-primary">
            Back to dashboard
          </Link>
        </div>
      </EmptyState>
    </div>
  );
}
