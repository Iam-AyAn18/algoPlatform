import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function PriceChart({ data, symbol }) {
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        No chart data available
      </div>
    );
  }

  const chartData = data.map(bar => ({
    date: new Date(bar.timestamp).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' }),
    close: bar.close,
  }));

  const firstVal = chartData[0]?.close || 0;
  const lastVal = chartData[chartData.length - 1]?.close || 0;
  const isUp = lastVal >= firstVal;

  return (
    <div>
      <h3 className="text-sm font-medium text-gray-400 mb-2">{symbol} – Price Chart</h3>
      <ResponsiveContainer width="100%" height={220}>
        <AreaChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="colorClose" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={isUp ? '#22c55e' : '#ef4444'} stopOpacity={0.3} />
              <stop offset="95%" stopColor={isUp ? '#22c55e' : '#ef4444'} stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9ca3af' }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
          <YAxis
            domain={['auto', 'auto']}
            tick={{ fontSize: 10, fill: '#9ca3af' }}
            tickLine={false}
            axisLine={false}
            tickFormatter={v => `₹${v.toLocaleString('en-IN')}`}
            width={70}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px', fontSize: '12px' }}
            formatter={v => [`₹${v.toLocaleString('en-IN')}`, 'Close']}
          />
          <Area
            type="monotone"
            dataKey="close"
            stroke={isUp ? '#22c55e' : '#ef4444'}
            fill="url(#colorClose)"
            strokeWidth={2}
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
