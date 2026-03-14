import { useState, useEffect } from 'react';
import { listOrders } from '../api';
import { RefreshCw } from 'lucide-react';

const STATUS_COLORS = {
  EXECUTED: 'bg-green-900 text-green-300',
  PENDING: 'bg-yellow-900 text-yellow-300',
  REJECTED: 'bg-red-900 text-red-300',
  CANCELLED: 'bg-gray-700 text-gray-300',
};

export default function OrderBook({ refreshTrigger }) {
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      setOrders(await listOrders(50));
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [refreshTrigger]);

  const fmt = v => v != null ? `₹${v.toLocaleString('en-IN', { maximumFractionDigits: 2 })}` : '—';

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-white">Order Book</h2>
        <button onClick={load} className="text-gray-400 hover:text-white transition-colors">
          <RefreshCw size={16} />
        </button>
      </div>
      {loading ? (
        <div className="text-gray-400 text-sm">Loading orders…</div>
      ) : orders.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No orders yet</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-xs border-b border-gray-700">
                <th className="text-left py-2 pr-3">ID</th>
                <th className="text-left py-2 pr-3">Symbol</th>
                <th className="text-left py-2 pr-3">Side</th>
                <th className="text-left py-2 pr-3">Type</th>
                <th className="text-right py-2 pr-3">Qty</th>
                <th className="text-right py-2 pr-3">Price</th>
                <th className="text-left py-2 pr-3">Status</th>
                <th className="text-left py-2 pr-3">Strategy</th>
                <th className="text-left py-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {orders.map(o => (
                <tr key={o.id} className="border-b border-gray-800 hover:bg-gray-800/40">
                  <td className="py-2 pr-3 text-gray-400">{o.id}</td>
                  <td className="py-2 pr-3 font-medium text-white">{o.symbol}</td>
                  <td className={`py-2 pr-3 font-medium ${o.side === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{o.side}</td>
                  <td className="py-2 pr-3 text-gray-300">{o.order_type}</td>
                  <td className="text-right py-2 pr-3">{o.quantity}</td>
                  <td className="text-right py-2 pr-3">{fmt(o.executed_price || o.price)}</td>
                  <td className="py-2 pr-3">
                    <span className={`text-xs rounded-full px-2 py-0.5 ${STATUS_COLORS[o.status] || 'bg-gray-700'}`}>
                      {o.status}
                    </span>
                  </td>
                  <td className="py-2 pr-3 text-gray-400 text-xs">{o.strategy || '—'}</td>
                  <td className="py-2 text-gray-400 text-xs">
                    {new Date(o.created_at).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
