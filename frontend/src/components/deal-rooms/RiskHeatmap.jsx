import DealRoomCard from './DealRoomCard';

export default function RiskHeatmap({ rooms }) {
  if (!rooms || rooms.length === 0) {
    return (
      <div className="text-center py-16 text-gray-400">
        <p className="text-4xl mb-3">📂</p>
        <p className="text-sm">No deal rooms yet. Create one to get started.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
      {rooms.map((room) => (
        <DealRoomCard key={room.id} room={room} />
      ))}
    </div>
  );
}
