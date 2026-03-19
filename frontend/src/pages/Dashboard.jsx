import { useState, useEffect, useCallback } from 'react';
import { getNifty50, getHistorical } from '../api';
import { useWebSocket } from '../hooks/useWebSocket';
import StockCard from '../components/StockCard';
import PriceChart from '../components/PriceChart';
import OrderPanel from '../components/OrderPanel';
import Watchlist from '../components/Watchlist';
import PortfolioView from '../components/PortfolioView';
import OrderBook from '../components/OrderBook';
import StrategySignal from '../components/StrategySignal';
import BacktestPanel from '../components/BacktestPanel';
import BrokerSettings from '../components/BrokerSettings';
import AlgoTrader from '../components/AlgoTrader';
import { RefreshCw, TrendingUp, Radio } from 'lucide-react';
import toast from 'react-hot-toast';

export default function Dashboard() {
  const [niftyQuotes, setNiftyQuotes] = useState([]);
  const [selectedSymbol, setSelectedSymbol] = useState({ symbol: 'RELIANCE', exchange: 'NSE' });
  const [chartData, setChartData] = useState([]);
  const [orderRefresh, setOrderRefresh] = useState(0);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [loadingMarket, setLoadingMarket] = useState(true);

  // Real-time WebSocket feed
  const { prices: livePrices, connected: wsConnected, lastSignal } = useWebSocket();

  // Merge live WS prices on top of the HTTP-fetched quote list.
  const mergedQuotes = niftyQuotes.map((q) => {
    const live = livePrices[q.symbol];
    if (!live) return q;
    return { ...q, ...live };
  });

  // Toast notifications for strategy signals arriving via WebSocket.
  useEffect(() => {
    if (!lastSignal) return;
    const { symbol, signal, strategy, confidence } = lastSignal;
    const emoji = signal === 'BUY' ? '🟢' : '🔴';
    toast(
      `${emoji} ${signal} signal on ${symbol}\n${strategy} · confidence ${(confidence * 100).toFixed(0)}%`,
      { duration: 6000 }
    );
  }, [lastSignal]);

  const loadMarket = useCallback(async () => {
    setLoadingMarket(true);
    try {
      setNiftyQuotes(await getNifty50());
    } catch {
      // ignore
    } finally {
      setLoadingMarket(false);
    }
  }, []);

  const loadChart = useCallback(async () => {
    try {
      const hist = await getHistorical(selectedSymbol.symbol, selectedSymbol.exchange, '1y', '1d');
      setChartData(hist.bars || []);
    } catch {
      setChartData([]);
    }
  }, [selectedSymbol]);

  useEffect(() => { loadMarket(); }, [loadMarket]);
  useEffect(() => { loadChart(); }, [loadChart]);

  const handleSelectSymbol = (symbol, exchange) => {
    setSelectedSymbol({ symbol, exchange });
  };

  const tabs = [
    { id: 'dashboard', label: 'Dashboard' },
    { id: 'portfolio', label: 'Portfolio' },
    { id: 'orders', label: 'Orders' },
    { id: 'strategies', label: 'Strategies' },
    { id: 'backtest', label: 'Backtest' },
    { id: 'algo', label: 'Algo Trading' },
    { id: 'broker', label: 'Broker' },
  ];

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Header */}
      <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-50">
        <div className="max-w-screen-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-green-600 rounded-lg flex items-center justify-center">
              <TrendingUp size={16} className="text-white" />
            </div>
            <span className="font-bold text-white text-lg">AlgoPlatform</span>
            <span className="text-xs bg-gray-800 text-gray-400 rounded px-2 py-0.5">NSE · BSE · Zerodha Kite</span>
            {/* Live feed indicator */}
            <span
              title={wsConnected ? 'Real-time feed active' : 'Connecting to real-time feed…'}
              className={`flex items-center gap-1 text-xs rounded px-2 py-0.5 ${
                wsConnected ? 'bg-green-900/40 text-green-400' : 'bg-gray-800 text-gray-500'
              }`}
            >
              <Radio size={10} className={wsConnected ? 'animate-pulse' : ''} />
              {wsConnected ? 'Live' : 'Offline'}
            </span>
          </div>
          <nav className="flex gap-1 overflow-x-auto">
            {tabs.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap
                  ${activeTab === tab.id
                    ? 'bg-green-600 text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}>
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-screen-2xl mx-auto px-4 py-6">

        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Market Overview */}
            <div>
              <div className="flex justify-between items-center mb-3">
                <h2 className="text-lg font-semibold text-white">
                  Market Overview{' '}
                  <span className="text-sm text-gray-500 font-normal">Nifty 50 Highlights</span>
                </h2>
                <button onClick={loadMarket} className="text-gray-400 hover:text-white transition-colors">
                  <RefreshCw size={16} className={loadingMarket ? 'animate-spin' : ''} />
                </button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3">
                {loadingMarket
                  ? Array(5).fill(0).map((_, i) => (
                      <div key={i} className="bg-gray-800 rounded-xl p-4 animate-pulse h-28" />
                    ))
                  : mergedQuotes.slice(0, 10).map(q => (
                      <div key={q.symbol} className="cursor-pointer" onClick={() => handleSelectSymbol(q.symbol, q.exchange)}>
                        <StockCard quote={q} live={!!livePrices[q.symbol]} />
                      </div>
                    ))
                }
              </div>
            </div>

            {/* Main layout: Chart + Order + Watchlist */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Chart */}
              <div className="lg:col-span-2 bg-gray-900 rounded-2xl p-5 border border-gray-800">
                <PriceChart data={chartData} symbol={selectedSymbol.symbol} />
              </div>

              {/* Right column: Watchlist + Order Panel */}
              <div className="space-y-6">
                <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
                  <Watchlist onSelectSymbol={handleSelectSymbol} />
                </div>
                <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
                  <h3 className="font-semibold text-white mb-4">Place Order</h3>
                  <OrderPanel onOrderPlaced={() => setOrderRefresh(r => r + 1)} />
                </div>
              </div>
            </div>

            {/* Order Book preview */}
            <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
              <OrderBook refreshTrigger={orderRefresh} />
            </div>
          </div>
        )}

        {/* Portfolio Tab */}
        {activeTab === 'portfolio' && (
          <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
            <PortfolioView />
          </div>
        )}

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-gray-900 rounded-2xl p-5 border border-gray-800">
              <h3 className="font-semibold text-white mb-4">Place Order</h3>
              <OrderPanel onOrderPlaced={() => setOrderRefresh(r => r + 1)} />
            </div>
            <div className="lg:col-span-2 bg-gray-900 rounded-2xl p-5 border border-gray-800">
              <OrderBook refreshTrigger={orderRefresh} />
            </div>
          </div>
        )}

        {/* Strategies Tab */}
        {activeTab === 'strategies' && (
          <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
            <StrategySignal />
          </div>
        )}

        {/* Backtest Tab */}
        {activeTab === 'backtest' && (
          <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
            <BacktestPanel />
          </div>
        )}

        {/* Algo Trading Tab */}
        {activeTab === 'algo' && (
          <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
            <AlgoTrader />
          </div>
        )}

        {/* Broker Settings Tab */}
        {activeTab === 'broker' && (
          <div className="bg-gray-900 rounded-2xl p-6 border border-gray-800">
            <BrokerSettings />
          </div>
        )}
      </main>
    </div>
  );
}

