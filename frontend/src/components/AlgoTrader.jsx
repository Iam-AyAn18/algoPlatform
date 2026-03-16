import { useState, useEffect, useCallback } from 'react';
import {
  listActionCenterOrders, approveOrder, rejectOrder, approveAllOrders,
  listWebhookSignals, sendWebhookSignal,
} from '../api';
import toast from 'react-hot-toast';
import { CheckCircle, XCircle, RefreshCw, Zap, Activity, Send } from 'lucide-react';

export default function AlgoTrader() {
  const [activeTab, setActiveTab] = useState('action-center');
  const [pendingOrders, setPendingOrders] = useState([]);
  const [webhookSignals, setWebhookSignals] = useState([]);
  const [loadingAC, setLoadingAC] = useState(false);
  const [loadingWH, setLoadingWH] = useState(false);
  const [testSignal, setTestSignal] = useState({
    symbol: 'RELIANCE', exchange: 'NSE', action: 'BUY', quantity: 1, strategy: 'test',
  });
  const [sendingTest, setSendingTest] = useState(false);

  const loadActionCenter = useCallback(async () => {
    setLoadingAC(true);
    try {
      setPendingOrders(await listActionCenterOrders());
    } catch (err) {
      toast.error('Failed to load action center: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setLoadingAC(false);
    }
  }, []);

  const loadWebhookSignals = useCallback(async () => {
    setLoadingWH(true);
    try {
      setWebhookSignals(await listWebhookSignals(50));
    } catch (err) {
      toast.error('Failed to load webhook signals: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setLoadingWH(false);
    }
  }, []);

  useEffect(() => {
    if (activeTab === 'action-center') loadActionCenter();
    if (activeTab === 'webhook') loadWebhookSignals();
  }, [activeTab, loadActionCenter, loadWebhookSignals]);

  async function handleApprove(orderId) {
    try {
      const updated = await approveOrder(orderId);
      toast.success(`Order #${orderId} approved → ${updated.status}`);
      loadActionCenter();
    } catch (err) {
      toast.error('Approve failed: ' + (err?.response?.data?.detail || err.message));
    }
  }

  async function handleReject(orderId) {
    try {
      await rejectOrder(orderId);
      toast.success(`Order #${orderId} rejected`);
      loadActionCenter();
    } catch (err) {
      toast.error('Reject failed: ' + (err?.response?.data?.detail || err.message));
    }
  }

  async function handleApproveAll() {
    try {
      const result = await approveAllOrders();
      toast.success(result.message);
      loadActionCenter();
    } catch (err) {
      toast.error('Approve all failed: ' + (err?.response?.data?.detail || err.message));
    }
  }

  async function handleSendTest(e) {
    e.preventDefault();
    setSendingTest(true);
    try {
      const result = await sendWebhookSignal(testSignal);
      toast.success(`Signal sent → Order #${result.order_id || '?'} (${result.status})`);
      loadWebhookSignals();
      if (activeTab === 'action-center') loadActionCenter();
    } catch (err) {
      toast.error('Signal failed: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setSendingTest(false);
    }
  }

  const tabs = [
    { id: 'action-center', label: 'Action Center', icon: CheckCircle },
    { id: 'webhook', label: 'Webhook Signals', icon: Activity },
    { id: 'test', label: 'Test Signal', icon: Zap },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white">Algo Trading</h2>
        <p className="text-sm text-gray-400 mt-1">
          Action Center for approving orders · Webhook receiver for TradingView / external signals
        </p>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 bg-gray-800 rounded-xl p-1">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => setActiveTab(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.id ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'}`}>
              <Icon size={14} />{tab.label}
              {tab.id === 'action-center' && pendingOrders.length > 0 && (
                <span className="bg-yellow-500 text-black text-xs font-bold px-1.5 py-0.5 rounded-full">
                  {pendingOrders.length}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Action Center */}
      {activeTab === 'action-center' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-white">Pending Orders</h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Orders queued for approval (semi-auto mode). Approve to route to broker.
              </p>
            </div>
            <div className="flex gap-2">
              {pendingOrders.length > 0 && (
                <button onClick={handleApproveAll}
                  className="bg-green-600 hover:bg-green-700 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors">
                  Approve All ({pendingOrders.length})
                </button>
              )}
              <button onClick={loadActionCenter}
                className="text-gray-400 hover:text-white p-1.5 rounded-lg transition-colors">
                <RefreshCw size={14} className={loadingAC ? 'animate-spin' : ''} />
              </button>
            </div>
          </div>

          {pendingOrders.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              <CheckCircle size={40} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">No pending orders</p>
              <p className="text-xs mt-1">Orders appear here when broker is in semi-auto mode</p>
            </div>
          ) : (
            <div className="space-y-2">
              {pendingOrders.map(order => (
                <div key={order.id}
                  className="flex items-center justify-between bg-gray-800 border border-yellow-700/40 rounded-xl p-4">
                  <div className="flex items-center gap-4">
                    <span className={`px-2 py-1 rounded-md text-xs font-bold ${order.side === 'BUY' ? 'bg-green-900/60 text-green-300' : 'bg-red-900/60 text-red-300'}`}>
                      {order.side}
                    </span>
                    <div>
                      <div className="text-white font-medium">{order.symbol} <span className="text-gray-400 text-xs">{order.exchange}</span></div>
                      <div className="text-xs text-gray-400">
                        {order.quantity} shares · {order.order_type}
                        {order.price && ` @ ₹${order.price}`}
                        {order.strategy && ` · ${order.strategy}`}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button onClick={() => handleApprove(order.id)}
                      className="flex items-center gap-1 bg-green-600 hover:bg-green-700 text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors">
                      <CheckCircle size={12} /> Approve
                    </button>
                    <button onClick={() => handleReject(order.id)}
                      className="flex items-center gap-1 bg-gray-700 hover:bg-red-700 text-gray-300 hover:text-white text-xs font-medium px-3 py-1.5 rounded-lg transition-colors">
                      <XCircle size={12} /> Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Webhook Signals */}
      {activeTab === 'webhook' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-medium text-white">Incoming Signals</h3>
              <p className="text-xs text-gray-400 mt-0.5">
                Webhook URL: <code className="bg-gray-800 px-1.5 py-0.5 rounded text-blue-400">POST /algo/webhook</code>
              </p>
            </div>
            <button onClick={loadWebhookSignals}
              className="text-gray-400 hover:text-white p-1.5 rounded-lg transition-colors">
              <RefreshCw size={14} className={loadingWH ? 'animate-spin' : ''} />
            </button>
          </div>

          {/* Webhook format info */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 text-xs text-gray-400">
            <p className="font-medium text-gray-300 mb-2">TradingView Alert JSON format:</p>
            <pre className="text-green-400 font-mono">{`{
  "symbol": "{{ticker}}",
  "exchange": "NSE",
  "action": "{{strategy.order.action}}",
  "quantity": 1,
  "strategy": "my_strategy"
}`}</pre>
            <p className="mt-2">Point your TradingView alert webhook URL to: <code className="text-blue-400">http://your-server:8000/algo/webhook</code></p>
          </div>

          {webhookSignals.length === 0 ? (
            <div className="text-center py-10 text-gray-500 text-sm">
              <Activity size={36} className="mx-auto mb-3 opacity-30" />
              No webhook signals received yet
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-700 text-gray-400 text-xs uppercase">
                    <th className="pb-2 text-left">#</th>
                    <th className="pb-2 text-left">Symbol</th>
                    <th className="pb-2 text-left">Action</th>
                    <th className="pb-2 text-right">Qty</th>
                    <th className="pb-2 text-left">Strategy</th>
                    <th className="pb-2 text-center">Status</th>
                    <th className="pb-2 text-right">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800">
                  {webhookSignals.map(sig => (
                    <tr key={sig.id} className="text-gray-300">
                      <td className="py-2 text-gray-500">{sig.id}</td>
                      <td className="py-2 font-medium text-white">{sig.symbol} <span className="text-gray-500 text-xs">{sig.exchange}</span></td>
                      <td className="py-2">
                        <span className={`px-2 py-0.5 rounded text-xs font-bold ${sig.action === 'BUY' ? 'bg-green-900/60 text-green-300' : 'bg-red-900/60 text-red-300'}`}>
                          {sig.action}
                        </span>
                      </td>
                      <td className="py-2 text-right">{sig.quantity}</td>
                      <td className="py-2 text-gray-400 text-xs">{sig.strategy || '—'}</td>
                      <td className="py-2 text-center">
                        {sig.processed
                          ? <span className="text-green-400 text-xs">✓ Processed</span>
                          : <span className="text-yellow-400 text-xs">Pending</span>
                        }
                      </td>
                      <td className="py-2 text-right text-xs text-gray-500">
                        {new Date(sig.received_at).toLocaleTimeString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Test Signal */}
      {activeTab === 'test' && (
        <div className="space-y-4">
          <div>
            <h3 className="text-sm font-medium text-white">Send Test Signal</h3>
            <p className="text-xs text-gray-400 mt-0.5">
              Simulate an incoming webhook signal to test your setup
            </p>
          </div>
          <form onSubmit={handleSendTest} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Symbol</label>
                <input type="text" value={testSignal.symbol}
                  onChange={e => setTestSignal(s => ({ ...s, symbol: e.target.value.toUpperCase() }))}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Exchange</label>
                <select value={testSignal.exchange}
                  onChange={e => setTestSignal(s => ({ ...s, exchange: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                  <option>NSE</option>
                  <option>BSE</option>
                  <option>NFO</option>
                  <option>MCX</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Action</label>
                <select value={testSignal.action}
                  onChange={e => setTestSignal(s => ({ ...s, action: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                  <option value="BUY">BUY</option>
                  <option value="SELL">SELL</option>
                  <option value="EXIT">EXIT</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Quantity</label>
                <input type="number" min="1" value={testSignal.quantity}
                  onChange={e => setTestSignal(s => ({ ...s, quantity: parseInt(e.target.value) }))}
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-400 mb-1.5">Strategy Tag</label>
              <input type="text" value={testSignal.strategy}
                onChange={e => setTestSignal(s => ({ ...s, strategy: e.target.value }))}
                placeholder="e.g. ma_crossover, rsi_14"
                className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
              />
            </div>
            <button type="submit" disabled={sendingTest}
              className="w-full flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg text-sm transition-colors">
              <Send size={14} />
              {sendingTest ? 'Sending...' : 'Send Test Signal'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
