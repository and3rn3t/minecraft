import { Link } from 'react-router-dom';
import { Button } from '../components/ui/Button';
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
      <Link to="/dashboard">
        <Button variant="primary">BACK TO DASHBOARD</Button>
      </Link>
    </Card>
  </div>
);

export default NotFound;
