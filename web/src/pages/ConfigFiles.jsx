import { useEffect, useState } from 'react';
import ConfigEditor from '../components/ConfigEditor';
import { Alert, ErrorState } from '../components/ui/Alert';
import { Card } from '../components/ui/Card';
import { EmptyState } from '../components/ui/EmptyState';
import { PageHeader } from '../components/ui/PageHeader';
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
        <div className="text-sm font-minecraft text-minecraft-text-light">
          LOADING CONFIGURATION FILES...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <PageHeader title="CONFIGURATION FILES" />

      {/* Error/Success messages */}
      {error && <ErrorState message={error} />}

      {saveMessage && (
        <Alert tone="success" autoDismiss={5000} onDismiss={() => setSaveMessage(null)}>
          {saveMessage}
        </Alert>
      )}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0">
        {/* File list */}
        <Card padding="md" className="lg:max-h-[calc(100vh-200px)] overflow-y-auto">
          <h2 className="text-sm font-minecraft uppercase text-minecraft-text-light mb-4">
            Files
          </h2>
          <div className="space-y-2">
            {files.map(file => (
              <button
                key={file.name}
                onClick={() => loadFileContent(file.name)}
                disabled={loadingContent}
                className={`w-full text-left px-3 py-2 text-[10px] font-minecraft disabled:opacity-50 disabled:cursor-not-allowed ${
                  selectedFile === file.name
                    ? 'bg-minecraft-grass text-white border-2 border-minecraft-grass-dark'
                    : 'bg-minecraft-dirt hover:bg-minecraft-dirt-light text-minecraft-text-light border-2 border-minecraft-dirt-dark'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-minecraft">{file.name}</span>
                  {file.exists ? (
                    <span className="text-[8px] text-minecraft-grass-light">●</span>
                  ) : (
                    <span className="text-[8px] text-minecraft-text-dark">○</span>
                  )}
                </div>
                {file.exists && file.size > 0 && (
                  <div className="text-[8px] font-minecraft text-minecraft-text-dark mt-1">
                    {(file.size / 1024).toFixed(1)} KB
                  </div>
                )}
              </button>
            ))}
          </div>
        </Card>

        {/* Editor */}
        <div className="lg:col-span-3 min-h-0 flex flex-col">
          {loadingContent && (
            <Card padding="none" className="flex items-center justify-center h-full">
              <div className="text-sm font-minecraft text-minecraft-text-light">
                LOADING FILE...
              </div>
            </Card>
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
            <Card padding="none" className="flex items-center justify-center h-full">
              <EmptyState icon="📄" title="No file selected" hint="Select a configuration file to edit" />
            </Card>
          )}
        </div>
      </div>

      {/* Warning */}
      <Alert tone="warning" className="mt-4">
        <strong>Warning:</strong> Changes to configuration files may require a server restart to
        take effect. Backups are automatically created before saving.
      </Alert>
    </div>
  );
};

export default ConfigFiles;
