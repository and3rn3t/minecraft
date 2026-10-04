const LoadingSkeleton = ({ lines = 3, className = '' }) => {
  return (
    <div className={`space-y-3 ${className}`}>
      {Array.from({ length: lines }).map((_, index) => (
        <div
          key={index}
          className="skeleton h-4 rounded-sm"
          style={{ width: index === lines - 1 ? '60%' : '100%' }}
        />
      ))}
    </div>
  );
};

export const CardSkeleton = () => {
  return (
    <div className="card-minecraft p-6 animate-pulse">
      <div className="skeleton h-4 w-1/3 mb-4 rounded-sm" />
      <div className="skeleton h-8 w-1/2 rounded-sm" />
    </div>
  );
};

export const StatusCardSkeleton = () => {
  return (
    <div className="card-minecraft p-6">
      <div className="flex items-center justify-between mb-2">
        <div className="skeleton h-3 w-24 rounded-sm" />
        <div className="skeleton h-6 w-6 rounded-sm" />
      </div>
      <div className="flex items-center gap-2">
        <div className="skeleton h-3 w-3 rounded-sm" />
        <div className="skeleton h-6 w-32 rounded-sm" />
      </div>
    </div>
  );
};

export default LoadingSkeleton;
