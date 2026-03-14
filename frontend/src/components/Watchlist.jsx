import { useState, useEffect } from 'react';
import { getWatchlist, addToWatchlist, removeFromWatchlist } from '../api';
import { Plus, Trash2, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Watchlist({ onSelectSymbol }) {
  const [items, setItems] = useState([]);
  const [input, setInput] = useState('');
  const [exchange, setExchange] = useState('NSE');
  const [loading, setLoading] = useState(false);

  const load = async () => {
    try {
      setItems(await getWatchlist());
    } catch {
      // ignore
    }
  };

  useEffect(() => { load(); }, []);

  const handleAdd = async () => {
    if (!input.trim()) return;
    setLoading(true);
    try {
      await addToWatchlist(input.trim().toUpperCase(), exchange);
      toast.success(`Added ${input.toUpperCase()} to watchlist`);
      setInput('');
      load();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add');
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (symbol) => {
    try {
      await removeFromWatchlist(symbol);
      toast.success(`Removed ${symbol}`);
      load();
    } catch {
      toast.error('Failed to remove');
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold text-white">Watchlist</h3>
        <button onClick={load} className="text-gray-400 hover:text-white transition-colors">
          <RefreshCw size={14} />
        </button>
      </div>

      {/* Add input */}
      <div className="flex gap-2 mb-4">
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleAdd()}
          placeholder="Symbol e.g. TCS"
          className="flex-1 bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-green-500"
        />
        <select value={exchange} onChange={e => setExchange(e.target.value)}
          className="bg-gray-700 border border-gray-600 rounded-lg px-2 py-2 text-sm text-white focus:outline-none focus:border-green-500">
          <option>NSE</option>
          <option>BSE</option>
        </select>
        <button onClick={handleAdd} disabled={loading}
          className="bg-green-600 hover:bg-green-500 text-white rounded-lg px-3 py-2 transition-colors disabled:opacity-50">
          <Plus size={16} />
        </button>
      </div>

      {/* Watchlist items */}
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {items.length === 0 && (
          <p className="text-gray-500 text-sm text-center py-4">Add stocks to your watchlist</p>
        )}
        {items.map(item => {
          const q = item.quote;
          const isPos = q?.change_pct >= 0;
          return (
            <div key={item.id}
              className="flex items-center justify-between p-3 bg-gray-700/50 rounded-lg hover:bg-gray-700 cursor-pointer transition-colors group"
              onClick={() => onSelectSymbol?.(item.symbol, item.exchange)}>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-white text-sm">{item.symbol}</span>
                  <span className="text-xs text-gray-500">{item.exchange}</span>
                </div>
                {q && (
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-white text-sm">₹{q.price?.toLocaleString('en-IN')}</span>
                    <span className={`text-xs flex items-center gap-0.5 ${isPos ? 'text-green-400' : 'text-red-400'}`}>
                      {isPos ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
                      {isPos ? '+' : ''}{q.change_pct?.toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
              <button onClick={e => { e.stopPropagation(); handleRemove(item.symbol); }}
                className="text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all ml-2">
                <Trash2 size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
