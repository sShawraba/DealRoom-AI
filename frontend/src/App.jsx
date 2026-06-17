import { Routes, Route, Navigate } from "react-router-dom";

function Dashboard() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">DealRoom AI</h1>
        <p className="mt-2 text-gray-500">Dashboard coming soon</p>
      </div>
    </div>
  );
}

function Login() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900">DealRoom AI</h1>
        <p className="mt-2 text-gray-500">Login coming soon</p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/login" element={<Login />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
