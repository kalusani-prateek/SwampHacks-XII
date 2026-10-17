// Shown for unknown URLs and for valid URLs whose resource doesn't exist
// (e.g. /sites/no-such-plant, or a 404 from the REST API).
import { Link } from 'react-router-dom';
import PageHeader from '../components/common/PageHeader.jsx';
import { urls } from '../routes.js';

export default function NotFoundPage({ title = 'Page not found', message = "This page doesn't exist or has moved." }) {
  return (
    <div className="card mx-auto max-w-lg text-center">
      <PageHeader title={title} />
      <p className="-mt-3 mb-5 text-sm text-slate-600">{message}</p>
      <div className="flex justify-center gap-2">
        <Link to={urls.home()} className="btn-primary">
          Go home
        </Link>
        <Link to={urls.sites()} className="btn-secondary">
          All sites
        </Link>
      </div>
    </div>
  );
}
