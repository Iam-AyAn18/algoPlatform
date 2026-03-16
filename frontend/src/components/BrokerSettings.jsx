import { useState, useEffect } from 'react';
import { getBrokerSettings, updateBrokerSettings, testBrokerConnection, getBrokerFunds, getBrokerPositions, getBrokerOrders } from '../api';
import toast from 'react-hot-toast';
import { Settings, Wifi, WifiOff, RefreshCw, DollarSign, BarChart2, BookOpen, CheckCircle, XCircle } from 'lucide-react';

const TRADE_MODES = [
  { value: 'paper', label: 'Paper Trading', desc: 'Simulated trades only – no real orders sent' },
  { value: 'semi_auto', label: 'Semi-Auto (Action Center)', desc: 'Real orders queued for your manual approval' },
  { value: 'auto', label: 'Auto (Live Trading)', desc: '⚠️ Real orders executed immediately via broker' },
];

const PRODUCTS = [
  { value: 'CNC', label: 'CNC – Cash & Carry (Delivery)' },
  { value: 'MIS', label: 'MIS – Margin Intraday Square-off' },
  { value: 'NRML', label: 'NRML – Normal (F&O Carry Forward)' },
];

export default function BrokerSettings() {
  const [settings, setSettings] = useState({ host: '', api_key: '', trade_mode: 'paper', default_product: 'CNC' });
  const [connected, setConnected] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [funds, setFunds] = useState(null);
  const [positions, setPositions] = useState(null);
  const [brokerOrders, setBrokerOrders] = useState(null);
  const [activeTab, setActiveTab] = useState('settings');

  useEffect(() => { loadSettings(); }, []);

  async function loadSettings() {
    try {
      const data = await getBrokerSettings();
      setSettings({
        host: data.host || 'http://127.0.0.1:5000',
        api_key: '',          // never pre-fill masked key; user must re-enter to change
        trade_mode: data.trade_mode || 'paper',
        default_product: data.default_product || 'CNC',
      });
      setConnected(data.connected);
      setLastUpdated(data.updated_at);
    } catch {
      // settings not yet saved
    }
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const data = await updateBrokerSettings(settings);
      setConnected(data.connected);
      setLastUpdated(data.updated_at);
      toast.success(data.connected ? '✅ Broker connected and settings saved' : '⚠️ Settings saved but connection failed');
    } catch (err) {
      toast.error('Failed to save settings: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    try {
      const data = await testBrokerConnection();
      setConnected(data.connected);
      if (data.connected) {
        toast.success('✅ Connected to OpenAlgo at ' + data.host);
      } else {
        toast.error('❌ ' + (data.message || 'Connection failed'));
      }
    } catch (err) {
      toast.error('Test failed: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setTesting(false);
    }
  }

  async function loadFunds() {
    try {
      const data = await getBrokerFunds();
      setFunds(data);
    } catch (err) {
      toast.error('Failed to fetch funds: ' + (err?.response?.data?.detail || err.message));
    }
  }

  async function loadPositions() {
    try {
      const data = await getBrokerPositions();
      setPositions(data);
    } catch (err) {
      toast.error('Failed to fetch positions: ' + (err?.response?.data?.detail || err.message));
    }
  }

  async function loadBrokerOrders() {
    try {
      const data = await getBrokerOrders();
      setBrokerOrders(data);
    } catch (err) {
      toast.error('Failed to fetch orders: ' + (err?.response?.data?.detail || err.message));
    }
  }

  const tabs = [
    { id: 'settings', label: 'Connection', icon: Settings },
    { id: 'funds', label: 'Funds', icon: DollarSign },
    { id: 'positions', label: 'Positions', icon: BarChart2 },
    { id: 'orders', label: 'Broker Orders', icon: BookOpen },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Broker Settings</h2>
          <p className="text-sm text-gray-400 mt-1">
            Connect to an{' '}
            <a href="https://github.com/marketcalls/openalgo" target="_blank" rel="noopener noreferrer"
               className="text-blue-400 hover:text-blue-300 underline">OpenAlgo</a>{' '}
            server to enable real broker order execution.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {connected
            ? <span className="flex items-center gap-1.5 text-green-400 text-sm font-medium bg-green-900/30 px-3 py-1.5 rounded-lg border border-green-700">
                <Wifi size={14} /> Connected
              </span>
            : <span className="flex items-center gap-1.5 text-gray-400 text-sm font-medium bg-gray-800 px-3 py-1.5 rounded-lg border border-gray-700">
                <WifiOff size={14} /> Disconnected
              </span>
          }
        </div>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 bg-gray-800 rounded-xl p-1">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => { setActiveTab(tab.id); if (tab.id === 'funds') loadFunds(); if (tab.id === 'positions') loadPositions(); if (tab.id === 'orders') loadBrokerOrders(); }}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.id ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'}`}>
              <Icon size={14} />{tab.label}
            </button>
          );
        })}
      </div>

      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <form onSubmit={handleSave} className="space-y-5">
          {/* OpenAlgo Host */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">OpenAlgo Server URL</label>
            <input
              type="url"
              value={settings.host}
              onChange={e => setSettings(s => ({ ...s, host: e.target.value }))}
              placeholder="http://127.0.0.1:5000"
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">The URL of your self-hosted OpenAlgo server (e.g. http://127.0.0.1:5000)</p>
          </div>

          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">OpenAlgo API Key</label>
            <input
              type="password"
              value={settings.api_key}
              onChange={e => setSettings(s => ({ ...s, api_key: e.target.value }))}
              placeholder="Enter your OpenAlgo API key"
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500"
            />
            <p className="mt-1 text-xs text-gray-500">Found in OpenAlgo → Profile → API Key. Leave blank to keep existing key.</p>
          </div>

          {/* Trading Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Trading Mode</label>
            <div className="space-y-2">
              {TRADE_MODES.map(mode => (
                <label key={mode.value}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                    settings.trade_mode === mode.value
                      ? 'border-blue-500 bg-blue-900/20'
                      : 'border-gray-700 bg-gray-800 hover:border-gray-600'
                  }`}>
                  <input type="radio" name="trade_mode" value={mode.value}
                    checked={settings.trade_mode === mode.value}
                    onChange={e => setSettings(s => ({ ...s, trade_mode: e.target.value }))}
                    className="mt-0.5 accent-blue-500"
                  />
                  <div>
                    <div className="text-sm font-medium text-white">{mode.label}</div>
                    <div className="text-xs text-gray-400 mt-0.5">{mode.desc}</div>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Default Product */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Default Product Type</label>
            <select
              value={settings.default_product}
              onChange={e => setSettings(s => ({ ...s, default_product: e.target.value }))}
              className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2.5 text-sm focus:outline-none focus:border-blue-500">
              {PRODUCTS.map(p => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3 pt-2">
            <button type="submit" disabled={saving}
              className="flex-1 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium py-2.5 rounded-lg text-sm transition-colors">
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
            <button type="button" onClick={handleTest} disabled={testing}
              className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white font-medium px-4 py-2.5 rounded-lg text-sm transition-colors">
              <RefreshCw size={14} className={testing ? 'animate-spin' : ''} />
              {testing ? 'Testing...' : 'Test Connection'}
            </button>
          </div>

          {/* Info box */}
          <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 text-xs text-gray-400 space-y-1.5">
            <p className="font-medium text-gray-300">How to set up OpenAlgo:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>Clone and run <span className="text-blue-400">github.com/marketcalls/openalgo</span></li>
              <li>Add your broker (Zerodha, AngelOne, etc.) in OpenAlgo settings</li>
              <li>Copy your API key from OpenAlgo → Profile</li>
              <li>Enter the URL and API key above and save</li>
            </ol>
            <p className="mt-2 text-yellow-400/80">⚠️ Auto mode will place real orders with real money. Use paper mode for testing.</p>
          </div>
        </form>
      )}

      {/* Funds Tab */}
      {activeTab === 'funds' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-medium text-gray-300">Account Funds & Margin</h3>
            <button onClick={loadFunds} className="text-gray-400 hover:text-white">
              <RefreshCw size={14} />
            </button>
          </div>
          {!connected ? (
            <div className="text-center py-10 text-gray-500 text-sm">
              <WifiOff size={32} className="mx-auto mb-3 opacity-40" />
              Broker not connected. Configure your OpenAlgo settings first.
            </div>
          ) : funds ? (
            <div className="grid grid-cols-2 gap-3">
              {Object.entries(funds.data || {}).map(([key, val]) => (
                <div key={key} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <div className="text-xs text-gray-400 capitalize">{key.replace(/_/g, ' ')}</div>
                  <div className="text-lg font-bold text-white mt-1">₹{parseFloat(val || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6 text-gray-500 text-sm">Click refresh to load funds</div>
          )}
        </div>
      )}

      {/* Positions Tab */}
      {activeTab === 'positions' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-medium text-gray-300">Broker Positions</h3>
            <button onClick={loadPositions} className="text-gray-400 hover:text-white">
              <RefreshCw size={14} />
            </button>
          </div>
          {!connected ? (
            <div className="text-center py-10 text-gray-500 text-sm">
              <WifiOff size={32} className="mx-auto mb-3 opacity-40" />
              Broker not connected.
            </div>
          ) : positions ? (
            <pre className="bg-gray-800 rounded-lg p-4 text-xs text-gray-300 overflow-auto max-h-96">
              {JSON.stringify(positions, null, 2)}
            </pre>
          ) : (
            <div className="text-center py-6 text-gray-500 text-sm">Click refresh to load positions</div>
          )}
        </div>
      )}

      {/* Broker Orders Tab */}
      {activeTab === 'orders' && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-medium text-gray-300">Broker Order Book</h3>
            <button onClick={loadBrokerOrders} className="text-gray-400 hover:text-white">
              <RefreshCw size={14} />
            </button>
          </div>
          {!connected ? (
            <div className="text-center py-10 text-gray-500 text-sm">
              <WifiOff size={32} className="mx-auto mb-3 opacity-40" />
              Broker not connected.
            </div>
          ) : brokerOrders ? (
            <pre className="bg-gray-800 rounded-lg p-4 text-xs text-gray-300 overflow-auto max-h-96">
              {JSON.stringify(brokerOrders, null, 2)}
            </pre>
          ) : (
            <div className="text-center py-6 text-gray-500 text-sm">Click refresh to load orders</div>
          )}
        </div>
      )}
    </div>
  );
}
