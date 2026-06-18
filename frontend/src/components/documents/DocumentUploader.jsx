import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { upload } from '../../api/documents';

export default function DocumentUploader({ dealRoomId, onUploaded }) {
  const [uploads, setUploads] = useState([]);

  const onDrop = useCallback(
    async (acceptedFiles) => {
      for (const file of acceptedFiles) {
        const id = crypto.randomUUID();
        setUploads((u) => [...u, { id, name: file.name, progress: 0, error: null }]);
        try {
          const results = await upload(dealRoomId, [file], (e) => {
            const pct = Math.round((e.loaded / e.total) * 100);
            setUploads((u) => u.map((x) => (x.id === id ? { ...x, progress: pct } : x)));
          });
          setUploads((u) => u.filter((x) => x.id !== id));
          if (onUploaded) onUploaded(results);
        } catch (err) {
          const msg = err.response?.data?.detail ?? 'Upload failed';
          setUploads((u) => u.map((x) => (x.id === id ? { ...x, error: msg } : x)));
        }
      }
    },
    [dealRoomId, onUploaded],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'], 'text/csv': ['.csv'] },
  });

  return (
    <div className="space-y-3">
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-blue-400 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400 bg-gray-50'
        }`}
      >
        <input {...getInputProps()} />
        <p className="text-3xl mb-2">📄</p>
        <p className="text-sm text-gray-600">
          {isDragActive ? 'Drop files here…' : 'Drag & drop PDFs, XLSXs, CSVs, or click to browse'}
        </p>
      </div>

      {uploads.map((u) => (
        <div key={u.id} className="bg-white border border-gray-200 rounded-lg px-4 py-3">
          <div className="flex items-center justify-between mb-1">
            <span className="text-sm text-gray-700 truncate">{u.name}</span>
            {u.error ? (
              <span className="text-xs text-red-600">{u.error}</span>
            ) : (
              <span className="text-xs text-gray-500">{u.progress}%</span>
            )}
          </div>
          {!u.error && (
            <div className="w-full bg-gray-200 rounded-full h-1.5">
              <div
                className="bg-blue-500 h-1.5 rounded-full transition-all"
                style={{ width: `${u.progress}%` }}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
