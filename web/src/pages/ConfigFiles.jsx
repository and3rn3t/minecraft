import { useEffect, useState } from 'react';
import ConfigEditor from '../components/ConfigEditor';
import { api } from '../services/api';

const ConfigFiles = () => {
  const [files, setFiles] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState(null);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      setLoading(true);
      const data = await api.listConfigFiles();
      setFiles(data.files || []);
    } catch (err) {
      setError('Failed to load configuration files');
      console.error('Failed to load files:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadFileContent = async filename => {
    try {
      setLoadingContent(true);
      setError(null);
      setSaveMessage(null);
      const data = await api.getConfigFile(filename);
      setFileContent(data);
      setSelectedFile(filename);
    } catch (err) {
      setError(`Failed to load ${filename}: ${err.message || 'Unknown error'}`);
      console.error('Failed to load file:', err);
    } finally {
      setLoadingContent(false);
    }
  };

  const handleSave = async content => {
    if (!selectedFile) return;

    try {
      setError(null);
      const result = await api.saveConfigFile(selectedFile, content);

      // Reload file content to show saved version
      const updatedData = await api.getConfigFile(selectedFile);
      setFileContent(updatedData);

      setSaveMessage(
        result.backup
          ? `File saved successfully! Backup created: ${result.backup}`
          : 'File saved successfully!'
      );

      // Clear message after 5 seconds
      setTimeout(() => setSaveMessage(null), 5000);
    } catch (err) {
      throw new Error(err.response?.data?.error || 'Failed to save file');
    }
  };

  const handleCancel = () => {
    if (selectedFile && fileContent) {
      // Reset to original content
      setFileContent({ ...fileContent });
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-xl">Loading configuration files...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <h1 className="text-3xl font-bold mb-8">Configuration Files</h1>

      {/* Error/Success messages */}
      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded p-4 mb-6 text-red-300">
          {error}
        </div>
      )}

      {saveMessage && (
        <div className="bg-green-900/50 border border-green-700 rounded p-4 mb-6 text-green-300">
          {saveMessage}
        </div>
      )}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0">
        {/* File list */}
        <div className="bg-gray-800 rounded-lg p-4 lg:max-h-[calc(100vh-200px)] overflow-y-auto">
          <h2 className="text-xl font-semibold mb-4">Files</h2>
          <div className="space-y-2">
            {files.map(file => (
              <button
                key={file.name}
                onClick={() => loadFileContent(file.name)}
                disabled={loadingContent}
                className={`w-full text-left px-3 py-2 rounded transition-colors ${
                  selectedFile === file.name
                    ? 'bg-primary-600 text-white'
                    : 'bg-gray-700 hover:bg-gray-600 text-gray-300'
                } disabled:opacity-50 disabled:cursor-not-allowed`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium">{file.name}</span>
                  {file.exists ? (
                    <span className="text-xs text-green-400">●</span>
                  ) : (
                    <span className="text-xs text-gray-500">○</span>
                  )}
                </div>
                {file.exists && file.size > 0 && (
                  <div className="text-xs text-gray-400 mt-1">
                    {(file.size / 1024).toFixed(1)} KB
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Editor */}
        <div className="lg:col-span-3 min-h-0 flex flex-col">
          {loadingContent && (
            <div className="flex items-center justify-center h-full bg-gray-800 rounded-lg">
              <div className="text-xl">Loading file...</div>
            </div>
          )}
          {!loadingContent && selectedFile && fileContent && (
            <div className="flex-1 min-h-0">
              <ConfigEditor
                filename={selectedFile}
                content={fileContent.content}
                onSave={handleSave}
                onCancel={handleCancel}
              />
            </div>
          )}
          {!loadingContent && (!selectedFile || !fileContent) && (
            <div className="flex items-center justify-center h-full bg-gray-800 rounded-lg">
              <div className="text-center text-gray-400">
                <p className="text-lg mb-2">No file selected</p>
                <p className="text-sm">Select a configuration file to edit</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Warning */}
      <div className="mt-4 bg-yellow-900/30 border border-yellow-700 rounded p-3 text-yellow-300 text-sm">
        <strong>Warning:</strong> Changes to configuration files may require a server restart to
        take effect. Backups are automatically created before saving.
      </div>
    </div>
  );
};

export default ConfigFiles;
