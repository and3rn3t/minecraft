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
      <div className="card-minecraft p-4 flex items-center justify-between border-b-2 border-[#5D4037]">
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-minecraft text-minecraft-text-light leading-tight">
            {filename}
          </h3>
          {isModified && (
            <span className="text-[10px] font-minecraft text-[#F57C00] flex items-center gap-1">
              <span className="w-2 h-2 bg-[#F57C00]"></span>
              MODIFIED
            </span>
          )}
        </div>
        <div className="flex gap-2">
          {onCancel && (
            <button
              onClick={onCancel}
              disabled={saving}
              className="btn-minecraft text-[10px] disabled:opacity-50"
            >
              CANCEL
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={!isModified || saving}
            className="btn-minecraft-primary text-[10px] disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'SAVING...' : 'SAVE'}
          </button>
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="bg-[#C62828] border-2 border-[#B71C1C] p-3 m-4 text-white text-[10px] font-minecraft">
          {error}
        </div>
      )}

      {/* Editor */}
      <div className="flex-1 bg-minecraft-background-dark overflow-hidden border-2 border-[#5D4037]">
        <div className="flex h-full">
          {/* Line numbers */}
          <div className="w-12 bg-minecraft-dirt-DEFAULT text-minecraft-text-dark font-minecraft text-[10px] text-right pr-2 py-3 overflow-y-auto select-none border-r-2 border-[#5D4037]">
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
            className="flex-1 bg-transparent text-minecraft-text-light font-minecraft text-[10px] p-3 py-3 leading-6 resize-none focus:outline-none focus:ring-0 overflow-y-auto"
            spellCheck={false}
            wrap="off"
            style={{
              tabSize: 2,
            }}
          />
        </div>
      </div>

      {/* Footer */}
      <div className="bg-minecraft-dirt-DEFAULT px-4 py-2 text-[8px] font-minecraft text-minecraft-text-dark flex justify-between border-t-2 border-[#5D4037]">
        <span>LANGUAGE: {getLanguage().toUpperCase()}</span>
        <span>{content.split('\n').length} LINES</span>
      </div>
    </div>
  );
};

export default ConfigEditor;
