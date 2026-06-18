export default function CitationPanel({ citation, onClose }) {
  if (!citation) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="w-full max-w-md bg-white shadow-2xl border-l border-gray-200 flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h3 className="font-semibold text-gray-900 text-sm">Source Citation</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 text-xl leading-none">&times;</button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">Document</p>
            <p className="text-sm text-gray-700">{citation.document_name ?? citation.source ?? '—'}</p>
          </div>

          {citation.page_number != null && (
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">Page</p>
              <p className="text-sm text-gray-700">{citation.page_number}</p>
            </div>
          )}

          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-2">Excerpt</p>
            <blockquote className="bg-gray-50 border-l-4 border-blue-400 rounded-r-lg px-4 py-3 text-sm text-gray-700 leading-relaxed italic">
              {citation.chunk_text ?? citation.text ?? 'No text available.'}
            </blockquote>
          </div>

          {citation.similarity != null && (
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-wide font-medium mb-1">Relevance</p>
              <p className="text-sm text-gray-700">{(citation.similarity * 100).toFixed(1)}%</p>
            </div>
          )}
        </div>
      </div>
      <div className="flex-1 bg-black/20" onClick={onClose} />
    </div>
  );
}
