import { TrendingUp, TrendingDown } from 'lucide-react';

/**
 * StockCard – shows a quote tile.
 *
 * Props:
 *   quote  – QuoteResponse object
 *   live   – boolean; when true renders a green pulse dot indicating the
 *            price was just updated via the real-time WebSocket feed.
 */
export default function StockCard({ quote, live = false }) {
  if (!quote) return null;
  const isPositive = quote.change_pct >= 0;
  return (
    <div className="bg-gray-800 rounded-xl p-4 hover:bg-gray-750 transition-colors">
      <div className="flex justify-between items-start">
        <div>
          <div className="flex items-center gap-1.5">
            <p className="font-bold text-white">{quote.symbol}</p>
            {live && (
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
              </span>
            )}
          </div>
          <p className="text-xs text-gray-400 truncate max-w-[120px]">{quote.name}</p>
        </div>
        <span className="text-xs bg-gray-700 rounded px-2 py-0.5 text-gray-300">{quote.exchange}</span>
      </div>
      <div className="mt-3 flex justify-between items-end">
        <p className="text-2xl font-bold text-white">₹{quote.price?.toLocaleString('en-IN')}</p>
        <div className={`flex items-center gap-1 text-sm font-medium ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
          {isPositive ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
          {isPositive ? '+' : ''}{quote.change_pct?.toFixed(2)}%
        </div>
      </div>
      <div className="mt-2 grid grid-cols-3 gap-1 text-xs text-gray-400">
        <span>O: ₹{quote.open?.toLocaleString('en-IN')}</span>
        <span>H: ₹{quote.high?.toLocaleString('en-IN')}</span>
        <span>L: ₹{quote.low?.toLocaleString('en-IN')}</span>
      </div>
    </div>
  );
}
