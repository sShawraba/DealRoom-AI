import { Routes, Route, Navigate, Outlet } from 'react-router-dom';
import useAuthStore from './store/authStore';
import Sidebar from './components/layout/Sidebar';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import DealRoom from './pages/DealRoom';
import Report from './pages/Report';
import AuditLog from './pages/AuditLog';

function ProtectedLayout() {
  const token = useAuthStore((s) => s.token);
  if (!token) return <Navigate to="/login" replace />;
  return (
    <div className="flex min-h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col min-h-screen overflow-auto bg-gray-50">
        <Outlet />
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedLayout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/deal-rooms/:roomId" element={<DealRoom />} />
        <Route path="/deal-rooms/:roomId/reports/:reportId" element={<Report />} />
        <Route path="/audit" element={<AuditLog />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
