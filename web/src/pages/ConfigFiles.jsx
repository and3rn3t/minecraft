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
        <div className="text-sm font-minecraft text-minecraft-text-light">
          LOADING CONFIGURATION FILES...
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        CONFIGURATION FILES
      </h1>

      {/* Error/Success messages */}
      {error && (
        <div className="bg-[#C62828] border-2 border-[#B71C1C] p-4 mb-6 text-white text-[10px] font-minecraft">
          {error}
        </div>
      )}

      {saveMessage && (
        <div className="bg-minecraft-grass-DEFAULT border-2 border-minecraft-grass-dark p-4 mb-6 text-white text-[10px] font-minecraft">
          {saveMessage}
        </div>
      )}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-4 gap-6 min-h-0">
        {/* File list */}
        <div className="card-minecraft p-4 lg:max-h-[calc(100vh-200px)] overflow-y-auto">
          <h2 className="text-sm font-minecraft text-minecraft-text-light mb-4 uppercase">
            FILES
          </h2>
          <div className="space-y-2">
            {files.map(file => (
              <button
                key={file.name}
                onClick={() => loadFileContent(file.name)}
                disabled={loadingContent}
                className={`w-full text-left px-3 py-2 text-[10px] font-minecraft disabled:opacity-50 disabled:cursor-not-allowed ${
                  selectedFile === file.name
                    ? 'bg-minecraft-grass-DEFAULT text-white border-2 border-minecraft-grass-dark'
                    : 'bg-minecraft-dirt-DEFAULT hover:bg-minecraft-dirt-light text-minecraft-text-light border-2 border-[#5D4037]'
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
        </div>

        {/* Editor */}
        <div className="lg:col-span-3 min-h-0 flex flex-col">
          {loadingContent && (
            <div className="flex items-center justify-center h-full card-minecraft">
              <div className="text-sm font-minecraft text-minecraft-text-light">
                LOADING FILE...
              </div>
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
            <div className="flex items-center justify-center h-full card-minecraft">
              <div className="text-center text-minecraft-text-dark">
                <p className="text-sm font-minecraft mb-2">NO FILE SELECTED</p>
                <p className="text-[10px] font-minecraft">SELECT A CONFIGURATION FILE TO EDIT</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Warning */}
      <div className="mt-4 bg-[#F57C00]/30 border-2 border-[#E65100] p-3 text-[10px] font-minecraft text-white">
        <strong>WARNING:</strong> CHANGES TO CONFIGURATION FILES MAY REQUIRE A SERVER RESTART TO
        TAKE EFFECT. BACKUPS ARE AUTOMATICALLY CREATED BEFORE SAVING.
      </div>
    </div>
  );
};

export default ConfigFiles;
