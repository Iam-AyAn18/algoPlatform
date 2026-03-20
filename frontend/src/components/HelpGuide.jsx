import { useState } from 'react';
import {
  BookOpen, TrendingUp, ShoppingCart, BarChart2, Zap, Settings,
  List, HelpCircle, ChevronDown, ChevronRight, Terminal, Star,
} from 'lucide-react';

const SECTIONS = [
  {
    id: 'quickstart',
    icon: <TrendingUp size={16} />,
    title: 'Quick Start',
    content: (
      <div className="space-y-4 text-sm text-gray-300">
        <p>
          <span className="font-semibold text-white">AlgoPlatform</span> is an open-source
          algorithmic trading platform for NSE &amp; BSE stocks. It ships with{' '}
          <span className="text-green-400">paper trading</span> (virtual ₹10 Lakh, no real
          money), live market data, strategy signals, backtesting, and optional Zerodha Kite
          Connect integration for real orders.
        </p>

        <div>
          <p className="font-semibold text-white mb-2">Start the platform</p>
          <div className="bg-gray-950 rounded-lg p-3 font-mono text-xs space-y-1">
            <p className="text-gray-500"># Terminal 1 – Backend (required)</p>
            <p className="text-green-400">cd backend</p>
            <p className="text-green-400">pip install -r requirements.txt</p>
            <p className="text-green-400">uvicorn app.main:app --reload --port 8000</p>
            <p className="mt-2 text-gray-500"># Terminal 2 – Frontend (optional)</p>
            <p className="text-green-400">cd frontend</p>
            <p className="text-green-400">npm install &amp;&amp; npm run dev</p>
          </div>
          <p className="mt-2 text-xs text-gray-400">
            Backend API: <code className="text-blue-400">http://localhost:8000</code> ·
            Interactive Swagger docs:{' '}
            <code className="text-blue-400">http://localhost:8000/docs</code> ·
            Frontend: <code className="text-blue-400">http://localhost:5173</code>
          </p>
        </div>

        <div>
          <p className="font-semibold text-white mb-2">30-second demo (curl)</p>
          <div className="bg-gray-950 rounded-lg p-3 font-mono text-xs space-y-1 text-green-400">
            <p className="text-gray-500"># 1. Check your starting balance (₹10 Lakh)</p>
            <p>curl http://localhost:8000/portfolio/</p>
            <p className="text-gray-500 mt-1"># 2. Get a live quote</p>
            <p>curl http://localhost:8000/market/quote/RELIANCE</p>
            <p className="text-gray-500 mt-1"># 3. Get a strategy signal</p>
            <p>curl "http://localhost:8000/strategies/signal/RELIANCE?strategy=RSI"</p>
            <p className="text-gray-500 mt-1"># 4. Place a BUY order (paper trade)</p>
            <p>{'curl -X POST http://localhost:8000/orders/ \\'}</p>
            <p>{'  -H "Content-Type: application/json" \\'}</p>
            <p>{'  -d \'{"symbol":"RELIANCE","side":"BUY","quantity":5}\''}</p>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 'dashboard',
    icon: <BarChart2 size={16} />,
    title: 'Dashboard Tab',
    content: (
      <div className="space-y-3 text-sm text-gray-300">
        <p>
          The <span className="text-white font-semibold">Dashboard</span> is the main screen.
          It shows a live Nifty 50 market overview, an interactive price chart, a watchlist,
          an order-placement panel, and your recent order book.
        </p>
        <ul className="list-disc list-inside space-y-1.5 text-gray-400">
          <li>
            <span className="text-white">Market Overview</span> — top 10 Nifty 50 stocks with
            live prices. Click any card to load its chart.
          </li>
          <li>
            <span className="text-white">Price Chart</span> — 1-year OHLCV candlestick chart for
            the selected stock. Powered by Recharts.
          </li>
          <li>
            <span className="text-white">Watchlist</span> — add stocks you want to monitor. Click
            a symbol to load its chart.
          </li>
          <li>
            <span className="text-white">Place Order</span> — enter a symbol, choose BUY / SELL,
            set quantity and order type, then click <em>Place Order</em>.
          </li>
          <li>
            <span className="text-white">Order Book</span> — your last 50 orders with status
            (EXECUTED / REJECTED / PENDING).
          </li>
          <li>
            <span className="text-white">Live indicator</span> — the green{' '}
            <em className="text-green-400">Live</em> badge in the header means a WebSocket feed
            is active; prices update automatically every 15 seconds.
          </li>
        </ul>
      </div>
    ),
  },
  {
    id: 'orders',
    icon: <ShoppingCart size={16} />,
    title: 'Placing Orders',
    content: (
      <div className="space-y-3 text-sm text-gray-300">
        <p>
          All orders are <span className="text-green-400">paper trades</span> by default —
          virtual money only. Connect a Zerodha account in the <strong>Broker</strong> tab for
          real orders.
        </p>

        <div>
          <p className="font-semibold text-white mb-1">Order types</p>
          <ul className="list-disc list-inside space-y-1 text-gray-400">
            <li><span className="text-white">MARKET</span> — fills immediately at the current live price.</li>
            <li><span className="text-white">LIMIT</span> — fills at your specified price.</li>
            <li><span className="text-white">STOP_LOSS</span> — triggers when the price reaches your stop level.</li>
          </ul>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Order flow</p>
          <ol className="list-decimal list-inside space-y-1 text-gray-400">
            <li>Go to <strong>Dashboard</strong> or the <strong>Orders</strong> tab.</li>
            <li>Type a symbol (e.g. <code className="text-blue-400">RELIANCE</code>), choose exchange (NSE / BSE).</li>
            <li>Select BUY or SELL, enter quantity, choose order type.</li>
            <li>Click <em>Place Order</em>. You'll see a toast notification with the result.</li>
          </ol>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Via curl</p>
          <div className="bg-gray-950 rounded-lg p-3 font-mono text-xs text-green-400 space-y-1">
            <p className="text-gray-500"># BUY 5 shares of RELIANCE at market price</p>
            <p>{'curl -X POST http://localhost:8000/orders/ \\'}</p>
            <p>{'  -H "Content-Type: application/json" \\'}</p>
            <p>{"  -d '{\"symbol\":\"RELIANCE\",\"exchange\":\"NSE\",\"side\":\"BUY\","}</p>
            <p>{"         \"order_type\":\"MARKET\",\"quantity\":5}'"}</p>
          </div>
        </div>

        <div className="bg-yellow-900/20 border border-yellow-700/40 rounded-lg p-3 text-xs text-yellow-300">
          <span className="font-semibold">Rejected orders?</span> A BUY is rejected when your
          cash balance is insufficient. A SELL is rejected when you don't hold the stock. Check
          the <strong>Portfolio</strong> tab to see your current cash and positions.
        </div>
      </div>
    ),
  },
  {
    id: 'portfolio',
    icon: <List size={16} />,
    title: 'Portfolio & P&L',
    content: (
      <div className="space-y-3 text-sm text-gray-300">
        <p>
          The <span className="text-white font-semibold">Portfolio</span> tab shows your cash
          balance, open positions, and both unrealised and realised P&amp;L.
        </p>

        <div>
          <p className="font-semibold text-white mb-1">P&amp;L explained</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="text-left pb-1 pr-3">Metric</th>
                  <th className="text-left pb-1">Meaning</th>
                </tr>
              </thead>
              <tbody className="space-y-1 text-gray-300">
                <tr className="border-b border-gray-800">
                  <td className="py-1.5 pr-3 text-white font-mono">unrealised_pnl</td>
                  <td className="py-1.5">(current_price − avg_buy_price) × qty. Paper profit, not yet locked in.</td>
                </tr>
                <tr className="border-b border-gray-800">
                  <td className="py-1.5 pr-3 text-white font-mono">realised_pnl</td>
                  <td className="py-1.5">Profit/loss from completed SELL trades. Locked in.</td>
                </tr>
                <tr>
                  <td className="py-1.5 pr-3 text-white font-mono">total_pnl</td>
                  <td className="py-1.5">(cash + current_value) − initial_capital.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <p className="text-xs text-gray-400">
          Use <span className="text-white font-semibold">Reset Portfolio</span> to wipe all
          positions and start fresh with ₹10 Lakh.
        </p>
      </div>
    ),
  },
  {
    id: 'strategies',
    icon: <Zap size={16} />,
    title: 'Strategy Signals',
    content: (
      <div className="space-y-3 text-sm text-gray-300">
        <p>
          The <span className="text-white font-semibold">Strategies</span> tab analyses a stock
          using a technical indicator and returns a <span className="text-green-400">BUY</span>,{' '}
          <span className="text-red-400">SELL</span>, or{' '}
          <span className="text-yellow-400">HOLD</span> signal with a confidence score (0–1).
        </p>

        <div>
          <p className="font-semibold text-white mb-1">Available strategies</p>
          <ul className="list-disc list-inside space-y-1 text-gray-400">
            <li><span className="text-white">MA_CROSSOVER</span> — Fast/slow SMA crossover (golden/death cross)</li>
            <li><span className="text-white">RSI</span> — Relative Strength Index; oversold &lt; 30 → BUY, overbought &gt; 70 → SELL</li>
            <li><span className="text-white">MACD</span> — Trend-following momentum indicator</li>
            <li><span className="text-white">BOLLINGER_BANDS</span> — Volatility-based mean reversion</li>
            <li><span className="text-white">STOCHASTIC</span> — Momentum oscillator</li>
          </ul>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">How to use</p>
          <ol className="list-decimal list-inside space-y-1 text-gray-400">
            <li>Go to the <strong>Strategies</strong> tab.</li>
            <li>Type a stock symbol and select an exchange.</li>
            <li>Pick a strategy from the dropdown and click <em>Get Signal</em>.</li>
            <li>Review the signal, confidence, and reasoning before placing an order.</li>
          </ol>
        </div>

        <div className="bg-gray-800 rounded-lg p-3 text-xs text-gray-400">
          ⚠️ Signals are for <strong>educational purposes</strong> only. They are not financial
          advice. Always do your own research before trading.
        </div>
      </div>
    ),
  },
  {
    id: 'backtest',
    icon: <BarChart2 size={16} />,
    title: 'Backtesting',
    content: (
      <div className="space-y-3 text-sm text-gray-300">
        <p>
          The <span className="text-white font-semibold">Backtest</span> tab lets you simulate a
          strategy on historical price data to see how it would have performed.
        </p>

        <div>
          <p className="font-semibold text-white mb-1">How to run a backtest</p>
          <ol className="list-decimal list-inside space-y-1 text-gray-400">
            <li>Select a symbol, exchange, and strategy.</li>
            <li>Choose a start date and end date (historical range).</li>
            <li>Set an initial capital amount (default ₹1 Lakh).</li>
            <li>Click <em>Run Backtest</em> and wait for results.</li>
          </ol>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Reading the results</p>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th className="text-left pb-1 pr-3">Metric</th>
                  <th className="text-left pb-1 pr-3">Good value</th>
                  <th className="text-left pb-1">Explanation</th>
                </tr>
              </thead>
              <tbody className="text-gray-300">
                <tr className="border-b border-gray-800">
                  <td className="py-1.5 pr-3 font-mono text-white">total_return_pct</td>
                  <td className="py-1.5 pr-3 text-green-400">&gt; 0%</td>
                  <td className="py-1.5">Overall gain vs. starting capital</td>
                </tr>
                <tr className="border-b border-gray-800">
                  <td className="py-1.5 pr-3 font-mono text-white">max_drawdown_pct</td>
                  <td className="py-1.5 pr-3 text-green-400">&lt; 20%</td>
                  <td className="py-1.5">Worst peak-to-trough loss</td>
                </tr>
                <tr className="border-b border-gray-800">
                  <td className="py-1.5 pr-3 font-mono text-white">sharpe_ratio</td>
                  <td className="py-1.5 pr-3 text-green-400">&gt; 1.0</td>
                  <td className="py-1.5">Risk-adjusted return</td>
                </tr>
                <tr>
                  <td className="py-1.5 pr-3 font-mono text-white">win_rate_pct</td>
                  <td className="py-1.5 pr-3 text-green-400">&gt; 50%</td>
                  <td className="py-1.5">% of profitable SELL trades</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    ),
  },
  {
    id: 'algo',
    icon: <Terminal size={16} />,
    title: 'Algo Trading (Webhooks)',
    content: (
      <div className="space-y-3 text-sm text-gray-300">
        <p>
          The <span className="text-white font-semibold">Algo Trading</span> tab lets you receive
          automated trading signals from external systems (e.g. TradingView) via webhooks.
        </p>

        <div>
          <p className="font-semibold text-white mb-1">Trade modes</p>
          <ul className="list-disc list-inside space-y-1 text-gray-400">
            <li><span className="text-white">paper</span> — signal processed as a paper trade only.</li>
            <li><span className="text-white">semi_auto</span> — signal queued in <em>Action Center</em> for manual review.</li>
            <li><span className="text-white">auto</span> — real order placed immediately via Zerodha (requires broker connection).</li>
          </ul>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Webhook format (TradingView)</p>
          <div className="bg-gray-950 rounded-lg p-3 font-mono text-xs text-green-400">
            <pre>{`{
  "symbol": "{{ticker}}",
  "exchange": "NSE",
  "action": "{{strategy.order.action}}",
  "quantity": 1,
  "strategy": "my_strategy"
}`}</pre>
          </div>
          <p className="mt-1.5 text-xs text-gray-400">
            Point the TradingView alert URL to:{' '}
            <code className="text-blue-400">POST http://your-server:8000/algo/webhook</code>
          </p>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Action Center</p>
          <p className="text-gray-400 text-xs">
            In <em>semi_auto</em> mode, incoming signals appear in the Action Center tab. Review
            each order, then click <strong>Approve</strong> to execute or <strong>Reject</strong>
            to discard it.
          </p>
        </div>
      </div>
    ),
  },
  {
    id: 'broker',
    icon: <Settings size={16} />,
    title: 'Zerodha Broker Setup',
    content: (
      <div className="space-y-3 text-sm text-gray-300">
        <p>
          AlgoPlatform connects <strong>directly</strong> to the Zerodha Kite Connect REST API —
          no intermediate server required. This is optional; the platform works fully in paper
          mode without a broker.
        </p>

        <div>
          <p className="font-semibold text-white mb-1">One-time setup</p>
          <ol className="list-decimal list-inside space-y-1 text-gray-400">
            <li>Create an app at <code className="text-blue-400">developers.kite.trade</code> → get API Key &amp; Secret.</li>
            <li>In the <strong>Broker</strong> tab, enter your API Key, API Secret, and Client ID.</li>
            <li>Click <em>Get Login URL</em> → log in with Zerodha credentials.</li>
            <li>The access token is saved automatically.</li>
          </ol>
        </div>

        <div>
          <p className="font-semibold text-white mb-1">Daily token refresh</p>
          <p className="text-gray-400 text-xs">
            Zerodha access tokens expire at midnight IST. Each trading day, click{' '}
            <em>Get Login URL</em> in the Broker tab and log in again to refresh your token.
          </p>
        </div>

        <div className="bg-gray-800 rounded-lg p-3 text-xs text-gray-400">
          ⚠️ <strong>Disclaimer:</strong> Real-money trading via Zerodha is entirely at your
          own risk. Always test in paper mode first.
        </div>
      </div>
    ),
  },
  {
    id: 'symbols',
    icon: <Star size={16} />,
    title: 'Common NSE Symbols',
    content: (
      <div className="space-y-3 text-sm text-gray-300">
        <p className="text-xs text-gray-400">
          Use these symbols in the Order, Strategy, and Backtest panels. For BSE, append{' '}
          <code className="text-blue-400">?exchange=BSE</code> to API calls or select BSE in
          the dropdown.
        </p>
        <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs">
          {[
            ['RELIANCE', 'Reliance Industries'],
            ['TCS', 'Tata Consultancy Services'],
            ['HDFCBANK', 'HDFC Bank'],
            ['INFY', 'Infosys'],
            ['ICICIBANK', 'ICICI Bank'],
            ['HINDUNILVR', 'Hindustan Unilever'],
            ['ITC', 'ITC'],
            ['SBIN', 'State Bank of India'],
            ['BHARTIARTL', 'Bharti Airtel'],
            ['KOTAKBANK', 'Kotak Mahindra Bank'],
            ['LT', 'Larsen & Toubro'],
            ['BAJFINANCE', 'Bajaj Finance'],
            ['ASIANPAINT', 'Asian Paints'],
            ['AXISBANK', 'Axis Bank'],
            ['MARUTI', 'Maruti Suzuki'],
            ['SUNPHARMA', 'Sun Pharmaceutical'],
            ['TITAN', 'Titan Company'],
            ['WIPRO', 'Wipro'],
            ['HCLTECH', 'HCL Technologies'],
            ['NESTLEIND', 'Nestlé India'],
          ].map(([sym, name]) => (
            <div key={sym} className="flex items-baseline gap-1.5 py-0.5">
              <code className="text-blue-400 font-mono">{sym}</code>
              <span className="text-gray-500 truncate">{name}</span>
            </div>
          ))}
        </div>
      </div>
    ),
  },
];

function AccordionItem({ section, isOpen, onToggle }) {
  return (
    <div className="border border-gray-700 rounded-xl overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-800 hover:bg-gray-750 transition-colors text-left"
      >
        <div className="flex items-center gap-2.5 text-white font-medium text-sm">
          <span className="text-gray-400">{section.icon}</span>
          {section.title}
        </div>
        {isOpen
          ? <ChevronDown size={16} className="text-gray-400 flex-shrink-0" />
          : <ChevronRight size={16} className="text-gray-400 flex-shrink-0" />}
      </button>
      {isOpen && (
        <div className="px-4 py-4 bg-gray-900 border-t border-gray-700">
          {section.content}
        </div>
      )}
    </div>
  );
}

export default function HelpGuide() {
  const [openId, setOpenId] = useState('quickstart');

  const toggle = (id) => setOpenId(prev => (prev === id ? null : id));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 bg-blue-600/20 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5">
          <BookOpen size={20} className="text-blue-400" />
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">How to Use AlgoPlatform</h2>
          <p className="text-sm text-gray-400 mt-0.5">
            Step-by-step guide covering every feature. Click a section to expand it.
          </p>
        </div>
      </div>

      {/* Quick-links row */}
      <div className="flex flex-wrap gap-2">
        {SECTIONS.map(s => (
          <button
            key={s.id}
            onClick={() => setOpenId(s.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              openId === s.id
                ? 'bg-blue-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700'
            }`}
          >
            {s.icon}
            {s.title}
          </button>
        ))}
      </div>

      {/* Accordion */}
      <div className="space-y-2">
        {SECTIONS.map(s => (
          <AccordionItem
            key={s.id}
            section={s}
            isOpen={openId === s.id}
            onToggle={() => toggle(s.id)}
          />
        ))}
      </div>

      {/* Footer note */}
      <div className="flex items-start gap-2 bg-gray-800/60 border border-gray-700 rounded-xl p-4 text-xs text-gray-400">
        <HelpCircle size={14} className="text-gray-500 flex-shrink-0 mt-0.5" />
        <span>
          Full documentation:{' '}
          <code className="text-blue-400">README.md</code> ·{' '}
          <code className="text-blue-400">docs/TRADING_GUIDE.md</code> ·{' '}
          <code className="text-blue-400">docs/API_REFERENCE.md</code>. For the interactive
          API explorer, open{' '}
          <code className="text-blue-400">http://localhost:8000/docs</code> in your browser.
        </span>
      </div>
    </div>
  );
}
