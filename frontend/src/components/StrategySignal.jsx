import { useState } from 'react';
import { getSignal } from '../api';
import { Zap, TrendingUp, TrendingDown, Minus } from 'lucide-react';
import toast from 'react-hot-toast';

const SIGNAL_ICONS = {
  BUY: <TrendingUp size={18} className="text-green-400" />,
  SELL: <TrendingDown size={18} className="text-red-400" />,
  HOLD: <Minus size={18} className="text-yellow-400" />,
};

const SIGNAL_COLORS = {
  BUY: 'border-green-500 bg-green-950',
  SELL: 'border-red-500 bg-red-950',
  HOLD: 'border-yellow-500 bg-yellow-950',
};

export default function StrategySignal() {
  const [form, setForm] = useState({ symbol: '', exchange: 'NSE', strategy: 'MA_CROSSOVER' });
  const [signal, setSignal] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const handleGet = async () => {
    if (!form.symbol) return toast.error('Enter a symbol');
    setLoading(true);
    try {
      const result = await getSignal(form.symbol.toUpperCase(), form.exchange, form.strategy);
      setSignal(result);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to get signal');
    } finally {
      setLoading(false);
    }
  };

  const inputCls = 'bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500';

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-4">Strategy Signals</h2>
      <div className="flex flex-wrap gap-3 mb-4">
        <input name="symbol" value={form.symbol} onChange={handleChange}
          placeholder="Symbol e.g. INFY" className={`${inputCls} w-36`} />
        <select name="exchange" value={form.exchange} onChange={handleChange} className={inputCls}>
          <option>NSE</option><option>BSE</option>
        </select>
        <select name="strategy" value={form.strategy} onChange={handleChange} className={inputCls}>
          <option value="MA_CROSSOVER">MA Crossover</option>
          <option value="RSI">RSI</option>
          <option value="MACD">MACD</option>
        </select>
        <button onClick={handleGet} disabled={loading}
          className="flex items-center gap-2 bg-green-600 hover:bg-green-500 text-white rounded-lg px-4 py-2 text-sm transition-colors disabled:opacity-50">
          <Zap size={14} />
          {loading ? 'Analysing…' : 'Get Signal'}
        </button>
      </div>

      {signal && (
        <div className={`border rounded-xl p-5 ${SIGNAL_COLORS[signal.signal]}`}>
          <div className="flex items-center gap-3">
            {SIGNAL_ICONS[signal.signal]}
            <div>
              <span className="text-xs text-gray-400">{signal.strategy} · {signal.symbol}</span>
              <h3 className={`text-2xl font-bold ${signal.signal === 'BUY' ? 'text-green-400' : signal.signal === 'SELL' ? 'text-red-400' : 'text-yellow-400'}`}>
                {signal.signal}
              </h3>
            </div>
            <div className="ml-auto text-right">
              <p className="text-xs text-gray-400">Confidence</p>
              <p className="text-xl font-bold text-white">{(signal.confidence * 100).toFixed(0)}%</p>
            </div>
          </div>
          <p className="mt-3 text-sm text-gray-300">{signal.reason}</p>
          <p className="mt-2 text-xs text-gray-500">
            {new Date(signal.timestamp).toLocaleString('en-IN')}
          </p>
        </div>
      )}
    </div>
  );
}
