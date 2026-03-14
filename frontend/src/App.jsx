import { Toaster } from 'react-hot-toast';
import Dashboard from './pages/Dashboard';

export default function App() {
  return (
    <>
      <Toaster position="top-right" toastOptions={{
        style: { background: '#1f2937', color: '#f9fafb', border: '1px solid #374151' },
      }} />
      <Dashboard />
    </>
  );
}
