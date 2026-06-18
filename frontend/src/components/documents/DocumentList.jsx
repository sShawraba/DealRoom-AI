import useJobStatus from '../../hooks/useJobStatus';

const STATUS_STYLES = {
  queued:      'bg-gray-100 text-gray-600',
  in_progress: 'bg-yellow-100 text-yellow-700',
  indexed:     'bg-green-100 text-green-700',
  failed:      'bg-red-100 text-red-700',
  ready:       'bg-green-100 text-green-700',
};

function DocRow({ doc, onDelete }) {
  const isProcessing = doc.status === 'queued' || doc.status === 'in_progress';
  const { status: jobStatus } = useJobStatus(isProcessing ? doc.job_id : null, 3000);
  const displayStatus = jobStatus?.status ?? doc.status;

  return (
    <tr className="border-b border-gray-100 last:border-0">
      <td className="py-3 pr-4 text-sm text-gray-800 max-w-xs truncate">{doc.filename ?? doc.name}</td>
      <td className="py-3 pr-4">
        <span className={`inline-block text-xs font-medium px-2 py-0.5 rounded-full ${STATUS_STYLES[displayStatus] ?? STATUS_STYLES.queued}`}>
          {displayStatus ?? 'unknown'}
        </span>
      </td>
      <td className="py-3 text-xs text-gray-400">
        {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}
      </td>
      <td className="py-3 text-right">
        <button
          onClick={() => onDelete(doc.id)}
          className="text-xs text-red-500 hover:text-red-700"
        >
          Delete
        </button>
      </td>
    </tr>
  );
}

export default function DocumentList({ documents, onDelete }) {
  if (!documents || documents.length === 0) {
    return (
      <div className="text-center py-10 text-gray-400">
        <p className="text-2xl mb-2">📄</p>
        <p className="text-sm">No documents uploaded yet.</p>
      </div>
    );
  }

  return (
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
            <DocRow key={doc.id} doc={doc} onDelete={onDelete} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
