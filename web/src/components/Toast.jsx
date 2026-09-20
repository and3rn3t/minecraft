import { useEffect } from 'react';

const Toast = ({ id, message, type = 'info', onClose, duration = 5000 }) => {
  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose(id);
      }, duration);

      return () => clearTimeout(timer);
    }
  }, [id, duration, onClose]);

  const typeClasses = {
    success: 'toast-success',
    error: 'toast-error',
    info: 'toast-info',
    warning: 'toast-warning',
  };

  return (
    <div className={`toast ${typeClasses[type] || typeClasses.info}`}>
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-lg">
            {type === 'success' && '✅'}
            {type === 'error' && '❌'}
            {type === 'info' && 'ℹ️'}
            {type === 'warning' && '⚠️'}
          </span>
          <p className="text-[10px] font-minecraft text-white leading-tight">{message}</p>
        </div>
        <button
          onClick={() => onClose(id)}
          className="text-white hover:text-gray-200 text-lg font-minecraft px-2 transition-opacity"
          aria-label="Close"
        >
          ×
        </button>
      </div>
    </div>
  );
};

export default Toast;
