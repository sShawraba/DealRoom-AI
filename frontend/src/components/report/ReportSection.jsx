import ReportItem from './ReportItem';
import AnnotationBadge from '../annotations/AnnotationBadge';

export default function ReportSection({ section, dealRoomId, reportId, annotationsByItem = {}, isApproved, onCitationClick, onAnnotationClick, onAddAnnotation }) {
  const allAnnotations = section.items?.flatMap((item) => annotationsByItem[item.id] ?? []) ?? [];
  const unresolvedDisputed = allAnnotations.filter((a) => a.type === 'disputed' && !a.resolved).length;

  return (
    <section id={`section-${section.section_key ?? section.id}`} className="bg-white rounded-xl border border-gray-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-gray-900">{section.title ?? section.section_key}</h3>
          {unresolvedDisputed > 0 && (
            <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-red-100 text-red-700">
              {unresolvedDisputed} disputed
            </span>
          )}
          {allAnnotations.length > 0 && (
            <AnnotationBadge annotations={allAnnotations} onClick={() => onAnnotationClick?.(section.items?.[0]?.id)} />
          )}
        </div>
        {!isApproved && (
          <button
            onClick={() => onAddAnnotation?.(section)}
            className="text-xs text-blue-600 hover:text-blue-800"
          >
            + Annotate
          </button>
        )}
      </div>

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
              onAnnotationClick={onAnnotationClick}
            />
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-400 italic">No findings in this section.</p>
      )}
    </section>
  );
}
