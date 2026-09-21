import { Link } from 'react-router-dom';
import { Card } from '../components/ui/Card';

const NotFound = () => (
  <div className="min-h-screen flex items-center justify-center bg-minecraft-background p-4">
    <Card padding="lg" className="w-full max-w-md p-8 text-center">
      <div className="text-3xl mb-4" aria-hidden="true">
        ⛏️
      </div>
      <h1 className="text-xl font-minecraft text-minecraft-grass-light mb-2 leading-tight">
        404
      </h1>
      <p className="text-[10px] font-minecraft text-minecraft-text-light mb-6 leading-relaxed">
        THIS BLOCK HASN&apos;T BEEN MINED YET.
      </p>
      {/* A Button can't be nested inside Link — that's a <button> inside an
          <a>, invalid HTML and ambiguous to assistive tech — so this styles
          the link itself with the same primary-button recipe instead. */}
      <Link
        to="/dashboard"
        className="btn-minecraft-primary inline-flex items-center justify-center gap-2 text-[10px] px-4 py-2"
      >
        BACK TO DASHBOARD
      </Link>
    </Card>
  </div>
);

export default NotFound;
