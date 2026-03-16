import { useState, useEffect } from 'react';
import { getPortfolio, resetPortfolio } from '../api';
import { TrendingUp, TrendingDown, RefreshCw, RotateCcw } from 'lucide-react';
import toast from 'react-hot-toast';

function StatCard({ label, value, sub, positive }) {
  return (
    <div className="bg-gray-800 rounded-xl p-4">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
      {sub && (
        <p className={`text-sm mt-1 flex items-center gap-1 ${positive === true ? 'text-green-400' : positive === false ? 'text-red-400' : 'text-gray-400'}`}>
          {positive === true && <TrendingUp size={12} />}
          {positive === false && <TrendingDown size={12} />}
          {sub}
        </p>
      )}
    </div>
  );
}

export default function PortfolioView() {
  const [portfolio, setPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [resetting, setResetting] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      setPortfolio(await getPortfolio());
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleReset = async () => {
    if (!window.confirm('Reset your paper trading account? All positions will be cleared and cash restored to the initial capital.')) return;
    setResetting(true);
    try {
      const fresh = await resetPortfolio();
      setPortfolio(fresh);
      toast.success('Paper account reset – starting fresh!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reset failed');
    } finally {
      setResetting(false);
    }
  };

  useEffect(() => { load(); }, []);

  const fmt = v => `₹${v?.toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

  if (loading) return <div className="text-gray-400 text-sm">Loading portfolio…</div>;
  if (!portfolio) return <div className="text-red-400 text-sm">Failed to load portfolio</div>;

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold text-white">Portfolio Summary</h2>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            disabled={resetting}
            title="Reset paper trading account"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-red-900/60 hover:bg-red-800 text-red-300 hover:text-white transition-colors disabled:opacity-50"
          >
            <RotateCcw size={13} className={resetting ? 'animate-spin' : ''} />
            Reset Account
          </button>
          <button onClick={load} className="text-gray-400 hover:text-white transition-colors">
            <RefreshCw size={16} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        <StatCard label="Available Cash" value={fmt(portfolio.cash)} />
        <StatCard label="Invested" value={fmt(portfolio.invested)} />
        <StatCard label="Current Value" value={fmt(portfolio.current_value)} />
        <StatCard
          label="Total P&L"
          value={fmt(portfolio.total_pnl)}
          sub={`${portfolio.total_pnl_pct >= 0 ? '+' : ''}${portfolio.total_pnl_pct?.toFixed(2)}%`}
          positive={portfolio.total_pnl_pct >= 0 ? true : false}
        />
      </div>

      {portfolio.positions.length === 0 ? (
        <div className="text-center py-8 text-gray-500">No open positions</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-gray-400 text-xs border-b border-gray-700">
                <th className="text-left py-2 pr-4">Symbol</th>
                <th className="text-right py-2 pr-4">Qty</th>
                <th className="text-right py-2 pr-4">Avg Buy</th>
                <th className="text-right py-2 pr-4">CMP</th>
                <th className="text-right py-2 pr-4">Unrealised P&L</th>
                <th className="text-right py-2 pr-4">Realised P&L</th>
                <th className="text-right py-2">Value</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.positions.map(pos => (
                <tr key={pos.symbol} className="border-b border-gray-800 hover:bg-gray-800/40">
                  <td className="py-3 pr-4 font-medium text-white">{pos.symbol}</td>
                  <td className="text-right pr-4">{pos.quantity}</td>
                  <td className="text-right pr-4">{fmt(pos.avg_buy_price)}</td>
                  <td className="text-right pr-4">{fmt(pos.current_price)}</td>
                  <td className={`text-right pr-4 ${pos.unrealised_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {fmt(pos.unrealised_pnl)} ({pos.unrealised_pnl_pct >= 0 ? '+' : ''}{pos.unrealised_pnl_pct?.toFixed(2)}%)
                  </td>
                  <td className={`text-right pr-4 ${pos.realised_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {fmt(pos.realised_pnl)}
                  </td>
                  <td className="text-right text-white">{fmt(pos.total_value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
