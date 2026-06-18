export default function AnnotationBadge({ annotations = [], onClick }) {
  if (annotations.length === 0) return null;

  const hasDisputed = annotations.some((a) => a.type === 'disputed' && !a.resolved);
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full transition-colors ${
        hasDisputed
          ? 'bg-red-100 text-red-700 hover:bg-red-200'
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      }`}
    >
      {hasDisputed && <span>⚠</span>}
      {annotations.length}
    </button>
  );
}
