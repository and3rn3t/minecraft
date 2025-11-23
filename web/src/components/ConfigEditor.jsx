import { useEffect, useRef, useState } from 'react';

const ConfigEditor = ({ filename, content: initialContent, onSave, onCancel }) => {
  const [content, setContent] = useState(initialContent || '');
  const [isModified, setIsModified] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    setContent(initialContent || '');
    setIsModified(false);
    setError(null);
  }, [initialContent, filename]);

  const handleChange = e => {
    const newContent = e.target.value;
    setContent(newContent);
    setIsModified(newContent !== initialContent);
    setError(null);
  };

  const handleSave = async () => {
    if (!isModified) return;

    setSaving(true);
    setError(null);

    try {
      await onSave(content);
      setIsModified(false);
    } catch (err) {
      setError(err.message || 'Failed to save file');
    } finally {
      setSaving(false);
    }
  };

  const getLanguage = () => {
    if (filename.endsWith('.properties')) return 'properties';
    if (filename.endsWith('.yml') || filename.endsWith('.yaml')) return 'yaml';
    if (filename.endsWith('.json')) return 'json';
    return 'text';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="bg-gray-800 rounded-t-lg p-4 flex items-center justify-between border-b border-gray-700">
        <div className="flex items-center gap-4">
          <h3 className="text-lg font-semibold">{filename}</h3>
          {isModified && (
            <span className="text-sm text-yellow-400 flex items-center gap-1">
              <span className="w-2 h-2 bg-yellow-400 rounded-full"></span>
              Modified
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {onCancel && (
            <button
              onClick={onCancel}
              disabled={saving}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded transition-colors disabled:opacity-50"
            >
              Cancel
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={!isModified || saving}
            className="px-4 py-2 bg-primary-600 hover:bg-primary-700 rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded p-3 m-4 text-red-300">
          {error}
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 bg-gray-900 rounded-b-lg overflow-hidden">
        <div className="flex h-full">
          {/* Line numbers */}
          <div className="w-12 bg-gray-800 text-gray-500 font-mono text-sm text-right pr-2 py-3 overflow-y-auto select-none border-r border-gray-700">
            {content.split('\n').map((_, index) => (
              <div key={`line-${index}`} className="leading-6">
                {index + 1}
              </div>
            ))}
          </div>

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={content}
            onChange={handleChange}
            className="flex-1 bg-transparent text-gray-200 font-mono text-sm p-3 py-3 leading-6 resize-none focus:outline-none focus:ring-0 overflow-y-auto"
            spellCheck={false}
            wrap="off"
            style={{
              tabSize: 2,
            }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="bg-gray-800 rounded-b-lg px-4 py-2 text-xs text-gray-400 flex justify-between border-t border-gray-700">
        <span>Language: {getLanguage()}</span>
        <span>{content.split('\n').length} lines</span>
      </div>
    </div>
  );
};

export default ConfigEditor;
