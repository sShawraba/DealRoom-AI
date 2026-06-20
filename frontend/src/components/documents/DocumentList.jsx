import { useState } from 'react';
import PdfViewerModal from './PdfViewerModal';

const STATUS_STYLES = {
  uploaded:   'bg-gray-100 text-gray-600',
  processing: 'bg-yellow-100 text-yellow-700',
  indexed:    'bg-green-100 text-green-700',
  failed:     'bg-red-100 text-red-700',
};

const STATUS_LABELS = {
  uploaded:   'uploaded',
  processing: 'processing…',
  indexed:    'indexed',
  failed:     'failed',
};

function DocRow({ doc, dealRoomId, onDelete, onView }) {
  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-3 pr-4 text-sm text-gray-800 max-w-xs truncate">{doc.filename ?? doc.name}</td>
      <td className="py-3 pr-4">
        <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_STYLES[doc.status] ?? STATUS_STYLES.uploaded}`}>
          {STATUS_LABELS[doc.status] ?? doc.status ?? 'unknown'}
        </span>
      </td>
      <td className="py-3 text-xs text-gray-400">
        {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}
      </td>
      <td className="py-3 text-right">
        <div className="flex items-center justify-end gap-3">
          <button
            onClick={() => onView(doc)}
            className="text-xs text-blue-500 hover:text-blue-700"
          >
            View
          </button>
          <button
            onClick={() => {
              if (window.confirm(`Delete "${doc.filename ?? doc.name}"? This cannot be undone.`)) {
                onDelete(doc.id);
              }
            }}
            className="text-xs text-red-500 hover:text-red-700"
          >
            Delete
          </button>
        </div>
      </td>
    </tr>
  );
}

export default function DocumentList({ documents, dealRoomId, onDelete }) {
  const [viewingDoc, setViewingDoc] = useState(null);

  if (!documents || documents.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400">
        <p className="text-2xl mb-2">📄</p>
        <p className="text-sm">No documents uploaded yet.</p>
      </div>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="text-left text-xs text-gray-400 border-b border-gray-200">
              <th className="pb-2 pr-4 font-medium">File</th>
              <th className="pb-2 pr-4 font-medium">Status</th>
              <th className="pb-2 font-medium">Uploaded</th>
              <th className="pb-2" />
            </tr>
          </thead>
          <tbody>
            {documents.map((doc) => (
              <DocRow
                key={doc.id}
                doc={doc}
                dealRoomId={dealRoomId}
                onDelete={onDelete}
                onView={setViewingDoc}
              />
            ))}
          </tbody>
        </table>
      </div>

      {viewingDoc && (
        <PdfViewerModal
          dealRoomId={dealRoomId}
          doc={viewingDoc}
          onClose={() => setViewingDoc(null)}
        />
      )}
    </>
  );
}
