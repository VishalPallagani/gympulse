import { Navigate, Route, Routes } from 'react-router-dom';

import Admin from './pages/Admin';
import Dashboard from './pages/Dashboard';

function MissingRoute() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-ink px-6 text-white">
      <div className="w-full max-w-lg rounded-2xl border border-zinc-800 bg-surface p-8 text-center shadow-glow">
        <h1 className="font-heading text-5xl uppercase tracking-[0.2em] text-accent">GymPulse</h1>
        <p className="mt-4 font-body text-zinc-300">
          Open your personal dashboard link from WhatsApp. It looks like
          <span className="text-white"> /dashboard/your-token</span>.
        </p>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/dashboard/:token" element={<Dashboard />} />
      <Route path="/admin" element={<Admin />} />
      <Route path="/" element={<Navigate to="/dashboard/demo" replace />} />
      <Route path="*" element={<MissingRoute />} />
    </Routes>
  );
}
