import { useState, useEffect, useCallback } from 'react';
import { list } from '../api/dealRooms';
import Topbar from '../components/layout/Topbar';
import RiskHeatmap from '../components/deal-rooms/RiskHeatmap';
import CreateDealRoomModal from '../components/deal-rooms/CreateDealRoomModal';
import CompareModal from '../components/deal-rooms/CompareModal';
import Pagination from '../components/Pagination';

const SKELETON = Array.from({ length: 6 }, (_, i) => i);

function SkeletonCard() {
  return (
    <div className="rounded-xl border-2 border-gray-200 bg-gray-50 p-5 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4 mb-3" />
      <div className="h-8 bg-gray-200 rounded w-1/3 mb-3" />
      <div className="h-3 bg-gray-200 rounded w-1/2" />
    </div>
  );
}

export default function Dashboard() {
  const [rooms, setRooms] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [showCompare, setShowCompare] = useState(false);

  const fetchRooms = useCallback(async () => {
    setLoading(true);
    try {
      const data = await list({ page, page_size: 12 });
      setRooms(data.items ?? []);
      setTotal(data.total ?? 0);
    } catch {}
    finally { setLoading(false); }
  }, [page]);

  useEffect(() => { fetchRooms(); }, [fetchRooms]);

  const handleCreated = (room) => setRooms((prev) => [room, ...prev]);

  return (
    <>
      <Topbar title="Dashboard" breadcrumbs={[{ label: 'Dashboard' }]} />

      <main className="flex-1 px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Deal Rooms</h2>
            <p className="text-sm text-gray-500 mt-0.5">{total} total</p>
          </div>
          <div className="flex gap-3">
            {rooms.length >= 2 && (
              <button
                onClick={() => setShowCompare(true)}
                className="px-4 py-2 text-sm border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Compare
              </button>
            )}
            <button
              onClick={() => setShowCreate(true)}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors"
            >
              + New Deal Room
            </button>
          </div>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {SKELETON.map((i) => <SkeletonCard key={i} />)}
          </div>
        ) : (
          <RiskHeatmap rooms={rooms} />
        )}

        {!loading && total > 12 && (
          <div className="mt-8">
            <Pagination page={page} total={total} pageSize={12} onChange={setPage} />
          </div>
        )}
      </main>

      {showCreate && (
        <CreateDealRoomModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />
      )}
      {showCompare && (
        <CompareModal rooms={rooms} onClose={() => setShowCompare(false)} />
      )}
    </>
  );
}
