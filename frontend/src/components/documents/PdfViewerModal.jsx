import { useEffect, useState } from 'react';
import { download } from '../../api/documents';

export default function PdfViewerModal({ dealRoomId, doc, onClose }) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let url;
    download(dealRoomId, doc.id)
      .then((res) => {
        url = URL.createObjectURL(res.data);
        setBlobUrl(url);
      })
      .catch(() => setError('Failed to load document.'));

    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [dealRoomId, doc.id]);

  return (
    <div className="fixed inset-0 bg-black/60 flex flex-col z-50">
      <div className="flex items-center justify-between bg-white px-5 py-3 border-b border-gray-200 shrink-0">
        <span className="text-sm font-medium text-gray-800 truncate max-w-lg">{doc.filename}</span>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-gray-700 text-2xl leading-none ml-4"
        >
          &times;
        </button>
      </div>

      <div className="flex-1 bg-gray-100">
        {error && (
          <div className="flex items-center justify-center h-full text-red-600 text-sm">{error}</div>
        )}
        {!error && !blobUrl && (
          <div className="flex items-center justify-center h-full text-gray-400 text-sm">
            Loading…
          </div>
        )}
        {blobUrl && (
          <iframe
            src={blobUrl}
            title={doc.filename}
            className="w-full h-full border-0"
          />
        )}
      </div>
    </div>
  );
}
