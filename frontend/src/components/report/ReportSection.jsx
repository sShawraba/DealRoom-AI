import ReportItem from './ReportItem';

export default function ReportSection({
  section, dealRoomId, reportId, annotationsByItem = {},
  isApproved, onCitationClick, onRefreshAnnotations, onItemSaved,
}) {
  const allAnnotations = section.items?.flatMap((item) => annotationsByItem[item.id] ?? []) ?? [];
  const unresolvedDisputed = allAnnotations.filter((a) => a.type === 'disputed' && !a.resolved).length;
  const totalAnnotations = allAnnotations.length;

  return (
    <section
      id={`section-${section.section_key ?? section.id}`}
      className="bg-white rounded-xl border border-gray-200 px-6 pt-5 pb-6"
    >
      {/* Section header */}
      <div className="flex items-center gap-3 mb-5 pb-3 border-b border-gray-100">
        <h3 className="font-semibold text-gray-900 text-base">
          {section.title ?? section.section_key}
        </h3>
        {unresolvedDisputed > 0 && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700">
            {unresolvedDisputed} disputed
          </span>
        )}
        {totalAnnotations > 0 && unresolvedDisputed === 0 && (
          <span className="text-xs text-gray-400">
            {totalAnnotations} annotation{totalAnnotations !== 1 ? 's' : ''}
          </span>
        )}
      </div>

      {/* Document body — items flow as paragraphs, no dividers */}
      {section.items?.length > 0 ? (
        <div>
          {section.items.map((item) => (
            <ReportItem
              key={item.id}
              item={item}
              dealRoomId={dealRoomId}
              reportId={reportId}
              annotations={annotationsByItem[item.id] ?? []}
              isApproved={isApproved}
              onCitationClick={onCitationClick}
              onRefreshAnnotations={onRefreshAnnotations}
              onItemSaved={onItemSaved}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-400 italic">No findings in this section.</p>
      )}
    </section>
  );
}
