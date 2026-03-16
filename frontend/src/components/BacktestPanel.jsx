import { useState } from 'react';
import { runBacktest } from '../api';
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import toast from 'react-hot-toast';
import { PlayCircle } from 'lucide-react';

export default function BacktestPanel() {
  const [form, setForm] = useState({
    symbol: 'RELIANCE',
    exchange: 'NSE',
    strategy: 'MA_CROSSOVER',
    start_date: '2022-01-01',
    end_date: '2024-01-01',
    initial_capital: 100000,
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const handleRun = async () => {
    if (!form.symbol) return toast.error('Enter a symbol');
    setLoading(true);
    try {
      const res = await runBacktest({
        ...form,
        initial_capital: parseFloat(form.initial_capital),
      });
      setResult(res);
      toast.success('Backtest complete!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Backtest failed');
    } finally {
      setLoading(false);
    }
  };

  const inputCls = 'w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-green-500';
  const labelCls = 'text-xs text-gray-400 mb-1 block';
  const fmt = v => `₹${Number(v).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

  return (
    <div>
      <h2 className="text-lg font-semibold text-white mb-4">Backtesting Engine</h2>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
        <div>
          <label className={labelCls}>Symbol</label>
          <input name="symbol" value={form.symbol} onChange={handleChange} className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Exchange</label>
          <select name="exchange" value={form.exchange} onChange={handleChange} className={inputCls}>
            <option>NSE</option><option>BSE</option>
          </select>
        </div>
        <div>
          <label className={labelCls}>Strategy</label>
          <select name="strategy" value={form.strategy} onChange={handleChange} className={inputCls}>
            <option value="MA_CROSSOVER">MA Crossover</option>
            <option value="RSI">RSI</option>
            <option value="MACD">MACD</option>
            <option value="BOLLINGER_BANDS">Bollinger Bands</option>
            <option value="STOCHASTIC">Stochastic</option>
          </select>
        </div>
        <div>
          <label className={labelCls}>Start Date</label>
          <input type="date" name="start_date" value={form.start_date} onChange={handleChange} className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>End Date</label>
          <input type="date" name="end_date" value={form.end_date} onChange={handleChange} className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Initial Capital (₹)</label>
          <input type="number" name="initial_capital" value={form.initial_capital} onChange={handleChange} className={inputCls} />
        </div>
      </div>

      <button onClick={handleRun} disabled={loading}
        className="flex items-center gap-2 bg-green-600 hover:bg-green-500 text-white rounded-xl px-6 py-3 font-medium text-sm transition-colors disabled:opacity-50 mb-6">
        <PlayCircle size={18} />
        {loading ? 'Running Backtest…' : 'Run Backtest'}
      </button>

      {result && (
        <div className="space-y-6">
          {/* Stats Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: 'Final Value', value: fmt(result.final_value) },
              { label: 'Total Return', value: `${result.total_return_pct >= 0 ? '+' : ''}${result.total_return_pct?.toFixed(2)}%`,
                color: result.total_return_pct >= 0 ? 'text-green-400' : 'text-red-400' },
              { label: 'Sharpe Ratio', value: result.sharpe_ratio?.toFixed(3) },
              { label: 'Max Drawdown', value: `-${result.max_drawdown_pct?.toFixed(2)}%`, color: 'text-red-400' },
              { label: 'Total Trades', value: result.total_trades },
              { label: 'Win Rate', value: `${result.win_rate_pct?.toFixed(1)}%` },
              { label: 'Winning Trades', value: result.winning_trades },
              { label: 'Strategy', value: result.strategy },
            ].map(stat => (
              <div key={stat.label} className="bg-gray-800 rounded-xl p-4">
                <p className="text-xs text-gray-400">{stat.label}</p>
                <p className={`text-xl font-bold mt-1 ${stat.color || 'text-white'}`}>{stat.value}</p>
              </div>
            ))}
          </div>

          {/* Equity Curve */}
          <div className="bg-gray-800 rounded-xl p-4">
            <h3 className="text-sm font-medium text-gray-300 mb-3">Equity Curve</h3>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={result.equity_curve} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                <defs>
                  <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#22c55e" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#22c55e" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
                <YAxis tick={{ fontSize: 10, fill: '#9ca3af' }} tickLine={false} axisLine={false}
                  tickFormatter={v => `₹${(v / 1000).toFixed(0)}k`} width={55} />
                <Tooltip contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', fontSize: '12px' }}
                  formatter={v => [`₹${Number(v).toLocaleString('en-IN')}`, 'Portfolio']} />
                <Area type="monotone" dataKey="value" stroke="#22c55e" fill="url(#equityGrad)" strokeWidth={2} dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>

          {/* Trades Table */}
          {result.trades.length > 0 && (
            <div className="bg-gray-800 rounded-xl p-4">
              <h3 className="text-sm font-medium text-gray-300 mb-3">Trades ({result.trades.length})</h3>
              <div className="overflow-x-auto max-h-64">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-gray-400 text-xs border-b border-gray-700">
                      <th className="text-left py-2 pr-4">Date</th>
                      <th className="text-left py-2 pr-4">Action</th>
                      <th className="text-right py-2 pr-4">Price</th>
                      <th className="text-right py-2 pr-4">Qty</th>
                      <th className="text-right py-2">P&L</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.map((t, i) => (
                      <tr key={i} className="border-b border-gray-700/50">
                        <td className="py-1.5 pr-4 text-gray-400 text-xs">{new Date(t.date).toLocaleDateString('en-IN')}</td>
                        <td className={`py-1.5 pr-4 font-medium ${t.action === 'BUY' ? 'text-green-400' : 'text-red-400'}`}>{t.action}</td>
                        <td className="text-right py-1.5 pr-4">₹{t.price.toLocaleString('en-IN')}</td>
                        <td className="text-right py-1.5 pr-4">{t.quantity}</td>
                        <td className={`text-right py-1.5 ${t.pnl > 0 ? 'text-green-400' : t.pnl < 0 ? 'text-red-400' : 'text-gray-400'}`}>
                          {t.pnl !== 0 ? `₹${t.pnl.toLocaleString('en-IN', { maximumFractionDigits: 0 })}` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
