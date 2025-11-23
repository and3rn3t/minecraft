import { useEffect, useState } from 'react';
import { api } from '../services/api';

const FileBrowser = () => {
  const [currentPath, setCurrentPath] = useState('');
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileContent, setFileContent] = useState('');
  const [editing, setEditing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadFiles(currentPath);
  }, [currentPath]);

  const loadFiles = async path => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listFiles(path);
      if (data.success) {
        setFiles(data.files || []);
        setCurrentPath(data.path || '');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const handleFileClick = async file => {
    if (file.type === 'directory') {
      setCurrentPath(file.path);
      setSelectedFile(null);
      setFileContent('');
      setEditing(false);
    } else {
      try {
        setLoading(true);
        const data = await api.readFile(file.path);
        if (data.success) {
          setSelectedFile(file);
          setFileContent(data.content || '');
          setEditing(false);
        }
      } catch (err) {
        setError(err.response?.data?.error || 'Failed to read file');
      } finally {
        setLoading(false);
      }
    }
  };

  const handleSave = async () => {
    if (!selectedFile) return;

    try {
      setLoading(true);
      setError(null);
      const data = await api.writeFile(selectedFile.path, fileContent);
      if (data.success) {
        setEditing(false);
        alert('File saved successfully' + (data.backup ? ` (backup created)` : ''));
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to save file');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async file => {
    if (!confirm(`Are you sure you want to delete ${file.name}?`)) {
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const data = await api.deleteFile(file.path);
      if (data.success) {
        if (selectedFile && selectedFile.path === file.path) {
          setSelectedFile(null);
          setFileContent('');
        }
        loadFiles(currentPath);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete file');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async e => {
    const file = e.target.files[0];
    if (!file) return;

    try {
      setUploading(true);
      setError(null);
      const data = await api.uploadFile(currentPath, file);
      if (data.success) {
        loadFiles(currentPath);
        alert('File uploaded successfully');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to upload file');
    } finally {
      setUploading(false);
      e.target.value = ''; // Reset input
    }
  };

  const handleDownload = async file => {
    try {
      setLoading(true);
      const blob = await api.downloadFile(file.path);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = file.name;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to download file');
    } finally {
      setLoading(false);
    }
  };

  const navigateUp = () => {
    if (currentPath) {
      const parentPath = currentPath.split('/').slice(0, -1).join('/');
      setCurrentPath(parentPath);
    }
  };

  const formatSize = bytes => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
  };

  return (
    <div>
      <h1 className="text-2xl font-minecraft text-minecraft-grass-light mb-8 leading-tight">
        FILE BROWSER
      </h1>

      {error && (
        <div className="card-minecraft p-4 mb-6 bg-[#C62828] text-white">
          <div className="text-[10px] font-minecraft">{error}</div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* File List */}
        <div className="card-minecraft p-4">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              {currentPath && (
                <button onClick={navigateUp} className="btn-minecraft text-[10px]" title="Go up">
                  ↑
                </button>
              )}
              <span className="text-[10px] font-minecraft text-minecraft-text-light">
                {currentPath || 'ROOT'}
              </span>
            </div>
            <label className="btn-minecraft text-[10px] cursor-pointer">
              UPLOAD
              <input type="file" className="hidden" onChange={handleUpload} disabled={uploading} />
            </label>
          </div>

          {loading ? (
            <div className="text-center py-8 text-[10px] font-minecraft text-minecraft-text-light">
              LOADING...
            </div>
          ) : (
            <div className="font-minecraft text-[10px]">
              {files.length === 0 ? (
                <div className="text-center py-8 text-minecraft-text-dark">NO FILES</div>
              ) : (
                files.map((file, index) => (
                  <div
                    key={index}
                    className={`flex items-center justify-between p-2 mb-1 cursor-pointer hover:bg-minecraft-dirt-DEFAULT ${
                      selectedFile?.path === file.path ? 'bg-minecraft-grass-DEFAULT' : ''
                    }`}
                    onClick={() => handleFileClick(file)}
                  >
                    <div className="flex items-center gap-2 flex-1">
                      <span className="text-xs">{file.type === 'directory' ? '📁' : '📄'}</span>
                      <span className="text-minecraft-text-light">{file.name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      {file.type === 'file' && (
                        <>
                          <span className="text-minecraft-text-dark text-[8px]">
                            {formatSize(file.size)}
                          </span>
                          <button
                            onClick={e => {
                              e.stopPropagation();
                              handleDownload(file);
                            }}
                            className="btn-minecraft text-[8px] px-2"
                            title="Download"
                          >
                            ↓
                          </button>
                        </>
                      )}
                      <button
                        onClick={e => {
                          e.stopPropagation();
                          handleDelete(file);
                        }}
                        className="btn-minecraft text-[8px] px-2 bg-[#C62828]"
                        title="Delete"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>

        {/* File Content */}
        <div className="card-minecraft p-4">
          {selectedFile ? (
            <>
              <div className="flex items-center justify-between mb-4">
                <span className="text-[10px] font-minecraft text-minecraft-text-light">
                  {selectedFile.name}
                </span>
                <div className="flex gap-2">
                  {editing ? (
                    <>
                      <button
                        onClick={handleSave}
                        className="btn-minecraft text-[10px]"
                        disabled={loading}
                      >
                        SAVE
                      </button>
                      <button
                        onClick={() => {
                          setEditing(false);
                          loadFiles(currentPath);
                          handleFileClick(selectedFile);
                        }}
                        className="btn-minecraft text-[10px]"
                      >
                        CANCEL
                      </button>
                    </>
                  ) : (
                    <>
                      <button
                        onClick={() => setEditing(true)}
                        className="btn-minecraft text-[10px]"
                      >
                        EDIT
                      </button>
                      <button
                        onClick={() => handleDownload(selectedFile)}
                        className="btn-minecraft text-[10px]"
                      >
                        DOWNLOAD
                      </button>
                    </>
                  )}
                </div>
              </div>
              {editing ? (
                <textarea
                  value={fileContent}
                  onChange={e => setFileContent(e.target.value)}
                  className="w-full h-[500px] font-mono text-[10px] p-2 bg-minecraft-dirt-DEFAULT text-minecraft-text-light border-2 border-minecraft-stone-DEFAULT"
                  spellCheck={false}
                />
              ) : (
                <div className="font-mono text-[10px] overflow-auto max-h-[500px] bg-minecraft-dirt-DEFAULT p-2 text-minecraft-text-light whitespace-pre-wrap">
                  {fileContent || '(empty file)'}
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-20 text-minecraft-text-dark text-[10px] font-minecraft">
              SELECT A FILE TO VIEW
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default FileBrowser;
