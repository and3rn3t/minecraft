const LoadingSkeleton = ({ lines = 3, className = '' }) => {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className="skeleton h-4 rounded"
          style={{ width: index === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  );
};

export const CardSkeleton = () => {
  return (
    <div className="card-minecraft p-6 animate-pulse">
      <div className="skeleton h-4 w-1/3 mb-4 rounded" />
      <div className="skeleton h-8 w-1/2 rounded" />
    </div>
  );
};

export const StatusCardSkeleton = () => {
  return (
    <div className="card-minecraft p-6">
      <div className="flex items-center justify-between mb-2">
        <div className="skeleton h-3 w-24 rounded" />
        <div className="skeleton h-6 w-6 rounded" />
      </div>
      <div className="flex items-center gap-2">
        <div className="skeleton h-3 w-3 rounded" />
        <div className="skeleton h-6 w-32 rounded" />
      </div>
    </div>
  );
};

export default LoadingSkeleton;
