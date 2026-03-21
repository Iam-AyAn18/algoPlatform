import { useState, useEffect } from 'react';
import {
  getBrokerSettings, updateBrokerSettings, testBrokerConnection,
  getBrokerFunds, getBrokerPositions, getBrokerOrders,
} from '../api';
import toast from 'react-hot-toast';
import {
  Settings, Wifi, WifiOff, RefreshCw, DollarSign, BarChart2, BookOpen,
  ExternalLink, Key, ChevronRight,
} from 'lucide-react';

const TRADE_MODES = [
  { value: 'paper', label: 'Paper Trading', desc: 'Simulated trades only – no real orders sent to broker' },
  { value: 'semi_auto', label: 'Semi-Auto (Action Center)', desc: 'Real orders queued for your manual approval before sending' },
  { value: 'auto', label: 'Auto (Live Trading)', desc: '⚠️ Real orders executed immediately via your broker' },
];

const PRODUCTS = [
  { value: 'CNC', label: 'CNC – Cash & Carry (Delivery)' },
  { value: 'MIS', label: 'MIS – Margin Intraday Square-off' },
  { value: 'NRML', label: 'NRML – Normal (F&O Carry Forward)' },
];

export default function BrokerSettings() {
  const [form, setForm] = useState({
    broker_name: 'paper', api_key: '', api_secret: '', access_token: '',
    user_id: '', trade_mode: 'paper', default_product: 'CNC',
  });
  const [serverState, setServerState] = useState({ connected: false, api_key_masked: '', api_secret_set: false, access_token_set: false, user_id: '' });
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [loginUrl, setLoginUrl] = useState('');
  const [requestToken, setRequestToken] = useState('');
  const [exchanging, setExchanging] = useState(false);
  const [funds, setFunds] = useState(null);
  const [positions, setPositions] = useState(null);
  const [brokerOrders, setBrokerOrders] = useState(null);
  const [activeTab, setActiveTab] = useState('settings');

  useEffect(() => { loadSettings(); }, []);

  async function loadSettings() {
    try {
      const data = await getBrokerSettings();
      setForm(f => ({
        ...f,
        broker_name: data.broker_name || 'paper',
        user_id: data.user_id || '',
        trade_mode: data.trade_mode || 'paper',
        default_product: data.default_product || 'CNC',
        // Never prefill secrets; user must re-enter to change
        api_key: '', api_secret: '', access_token: '',
      }));
      setServerState(data);
    } catch {
      // settings not yet saved
    }
  }

  async function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    try {
      const data = await updateBrokerSettings(form);
      setServerState(data);
      toast.success(data.connected ? '✅ Broker connected and settings saved' : '💾 Settings saved');
    } catch (err) {
      toast.error('Failed to save: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setSaving(false);
    }
  }

  async function handleTest() {
    setTesting(true);
    try {
      const data = await testBrokerConnection();
      setServerState(s => ({ ...s, connected: data.connected }));
      if (data.connected) toast.success('✅ ' + data.message);
      else toast.error('❌ ' + (data.message || 'Connection failed'));
    } catch (err) {
      toast.error('Test failed: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setTesting(false);
    }
  }

  async function handleGetLoginUrl() {
    try {
      const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const resp = await fetch(`${BASE}/broker/login-url`);
      const json = await resp.json();
      if (json.login_url) {
        setLoginUrl(json.login_url);
        toast.success('Login URL generated – click the link to authenticate');
      } else {
        toast.error(json.detail || 'Failed to get login URL');
      }
    } catch (err) {
      toast.error('Failed to get login URL: ' + err.message);
    }
  }

  async function handleExchangeToken(e) {
    e.preventDefault();
    if (!requestToken.trim()) return;
    setExchanging(true);
    try {
      const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';
      const resp = await fetch(`${BASE}/broker/exchange-token?request_token=${encodeURIComponent(requestToken.trim())}`, { method: 'POST' });
      const json = await resp.json();
      if (json.connected) {
        toast.success('✅ ' + json.message);
        setServerState(s => ({ ...s, connected: true, access_token_set: true }));
        setRequestToken('');
        setLoginUrl('');
      } else {
        toast.error(json.detail || 'Token exchange failed');
      }
    } catch (err) {
      toast.error('Exchange failed: ' + err.message);
    } finally {
      setExchanging(false);
    }
  }

  async function loadFunds() {
    try { setFunds(await getBrokerFunds()); }
    catch (err) { toast.error(err?.response?.data?.detail || err.message); }
  }
  async function loadPositions() {
    try { setPositions(await getBrokerPositions()); }
    catch (err) { toast.error(err?.response?.data?.detail || err.message); }
  }
  async function loadBrokerOrders() {
    try { setBrokerOrders(await getBrokerOrders()); }
    catch (err) { toast.error(err?.response?.data?.detail || err.message); }
  }

  function handleTabChange(tabId) {
    setActiveTab(tabId);
    if (tabId === 'funds') loadFunds();
    else if (tabId === 'positions') loadPositions();
    else if (tabId === 'orders') loadBrokerOrders();
  }

  const tabs = [
    { id: 'settings', label: 'Connection', icon: Settings },
    { id: 'funds', label: 'Funds', icon: DollarSign },
    { id: 'positions', label: 'Positions', icon: BarChart2 },
    { id: 'orders', label: 'Order Book', icon: BookOpen },
  ];

  const isZerodha = form.broker_name === 'zerodha';
  const isGroww = form.broker_name === 'groww';
  const isBrokerConnectable = isZerodha || isGroww;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Broker Settings</h2>
          <p className="text-sm text-gray-400 mt-1">
            Connect directly to your broker – no intermediate server required.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {serverState.connected
            ? <span className="flex items-center gap-1.5 text-green-400 text-sm font-medium bg-green-900/30 px-3 py-1.5 rounded-lg border border-green-700">
                <Wifi size={14} /> Connected
              </span>
            : <span className="flex items-center gap-1.5 text-gray-400 text-sm font-medium bg-gray-800 px-3 py-1.5 rounded-lg border border-gray-700">
                <WifiOff size={14} /> Disconnected
              </span>
          }
        </div>
      </div>

      {/* Architecture explainer */}
      <div className="bg-blue-900/20 border border-blue-700/40 rounded-xl p-4 text-sm">
        <p className="text-blue-300 font-medium mb-1">How it works (no separate server needed)</p>
        <div className="flex items-center gap-2 text-gray-300 text-xs font-mono">
          <span className="bg-gray-800 px-2 py-1 rounded">AlgoPlatform</span>
          <ChevronRight size={12} className="text-blue-400" />
          <span className="bg-blue-900/50 px-2 py-1 rounded border border-blue-600">
            {isGroww ? 'Groww API' : 'Zerodha Kite API'}
          </span>
          <span className="text-gray-500 ml-1">(directly, no middleman)</span>
        </div>
        <p className="text-gray-500 text-xs mt-2">
          The platform calls the broker REST API directly using your API key and access token.
          No other software needs to be running.
        </p>
      </div>

      {/* Sub-tabs */}
      <div className="flex gap-1 bg-gray-800 rounded-xl p-1">
        {tabs.map(tab => {
          const Icon = tab.icon;
          return (
            <button key={tab.id} onClick={() => handleTabChange(tab.id)}
              className={`flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-sm font-medium transition-colors ${activeTab === tab.id ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-white'}`}>
              <Icon size={14} />{tab.label}
            </button>
          );
        })}
      </div>

      {/* Settings Tab */}
      {activeTab === 'settings' && (
        <form onSubmit={handleSave} className="space-y-5">
          {/* Broker Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Broker</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { value: 'paper', label: '📄 Paper Trading', desc: 'No real broker required' },
                { value: 'zerodha', label: '🟥 Zerodha Kite', desc: 'API at developers.kite.trade' },
                { value: 'groww', label: '🟢 Groww', desc: 'API at groww.in/open-api' },
              ].map(b => (
                <label key={b.value}
                  className={`flex flex-col gap-1 p-3 rounded-lg border cursor-pointer transition-colors ${form.broker_name === b.value ? 'border-blue-500 bg-blue-900/20' : 'border-gray-700 bg-gray-800 hover:border-gray-600'}`}>
                  <div className="flex items-center gap-2">
                    <input type="radio" name="broker_name" value={b.value}
                      checked={form.broker_name === b.value}
                      onChange={e => setForm(f => ({ ...f, broker_name: e.target.value }))}
                      className="accent-blue-500"
                    />
                    <span className="text-sm font-medium text-white">{b.label}</span>
                  </div>
                  <span className="text-xs text-gray-400 pl-5">{b.desc}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Zerodha credentials */}
          {isZerodha && (
            <div className="space-y-4 bg-gray-800/50 rounded-xl p-4 border border-gray-700">
              <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Zerodha Kite Connect Credentials</p>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">API Key</label>
                  <input type="password" value={form.api_key}
                    onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))}
                    placeholder={serverState.api_key_masked || 'Enter API key'}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">API Secret</label>
                  <input type="password" value={form.api_secret}
                    onChange={e => setForm(f => ({ ...f, api_secret: e.target.value }))}
                    placeholder={serverState.api_secret_set ? '••••••••' : 'Enter API secret'}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Zerodha Client ID (User ID)</label>
                <input type="text" value={form.user_id}
                  onChange={e => setForm(f => ({ ...f, user_id: e.target.value.toUpperCase() }))}
                  placeholder="e.g. AB1234"
                  className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                />
              </div>

              {/* Daily access token section */}
              <div className="border-t border-gray-700 pt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-gray-300">Daily Access Token</p>
                    <p className="text-xs text-gray-500">Valid until midnight IST – must be refreshed each trading day</p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${serverState.access_token_set ? 'bg-green-900/40 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
                    {serverState.access_token_set ? '✓ Token set' : 'Not set'}
                  </span>
                </div>

                {/* Option A: paste token directly */}
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Paste Access Token directly (if you have one)</label>
                  <input type="password" value={form.access_token}
                    onChange={e => setForm(f => ({ ...f, access_token: e.target.value }))}
                    placeholder="Paste today's access token"
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
                  />
                </div>

                {/* Option B: login flow */}
                <div className="bg-gray-900 rounded-lg p-3 space-y-2">
                  <p className="text-xs text-gray-400 font-medium">Or generate via Kite login flow:</p>
                  <div className="flex gap-2">
                    <button type="button" onClick={handleGetLoginUrl}
                      className="flex items-center gap-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
                      <Key size={12} /> Get Login URL
                    </button>
                    {loginUrl && (
                      <a href={loginUrl} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
                        <ExternalLink size={12} /> Open Login Page
                      </a>
                    )}
                  </div>
                  {loginUrl && (
                    <form onSubmit={handleExchangeToken} className="flex gap-2">
                      <input type="text" value={requestToken}
                        onChange={e => setRequestToken(e.target.value)}
                        placeholder="Paste request_token from callback URL"
                        className="flex-1 bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-blue-500"
                      />
                      <button type="submit" disabled={exchanging || !requestToken.trim()}
                        className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
                        {exchanging ? 'Exchanging...' : 'Get Access Token'}
                      </button>
                    </form>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Groww credentials */}
          {isGroww && (
            <div className="space-y-4 bg-gray-800/50 rounded-xl p-4 border border-gray-700">
              <p className="text-xs text-gray-400 font-medium uppercase tracking-wide">Groww Developer API Credentials</p>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Client ID (API Key)</label>
                  <input type="password" value={form.api_key}
                    onChange={e => setForm(f => ({ ...f, api_key: e.target.value }))}
                    placeholder={serverState.api_key_masked || 'Enter Groww Client ID'}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Client Secret</label>
                  <input type="password" value={form.api_secret}
                    onChange={e => setForm(f => ({ ...f, api_secret: e.target.value }))}
                    placeholder={serverState.api_secret_set ? '••••••••' : 'Enter Client Secret'}
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
                  />
                </div>
              </div>

              {/* Groww access token section */}
              <div className="border-t border-gray-700 pt-4 space-y-3">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs font-medium text-gray-300">Access Token</p>
                    <p className="text-xs text-gray-500">Obtained via Groww OAuth flow below</p>
                  </div>
                  <span className={`text-xs px-2 py-1 rounded ${serverState.access_token_set ? 'bg-green-900/40 text-green-400' : 'bg-gray-700 text-gray-400'}`}>
                    {serverState.access_token_set ? '✓ Token set' : 'Not set'}
                  </span>
                </div>

                {/* Option A: paste token directly */}
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-1.5">Paste Access Token directly (if you have one)</label>
                  <input type="password" value={form.access_token}
                    onChange={e => setForm(f => ({ ...f, access_token: e.target.value }))}
                    placeholder="Paste your Groww access token"
                    className="w-full bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-green-500"
                  />
                </div>

                {/* Option B: OAuth flow */}
                <div className="bg-gray-900 rounded-lg p-3 space-y-2">
                  <p className="text-xs text-gray-400 font-medium">Or generate via Groww OAuth flow:</p>
                  <div className="flex gap-2">
                    <button type="button" onClick={handleGetLoginUrl}
                      className="flex items-center gap-1.5 bg-gray-700 hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
                      <Key size={12} /> Get Login URL
                    </button>
                    {loginUrl && (
                      <a href={loginUrl} target="_blank" rel="noopener noreferrer"
                        className="flex items-center gap-1.5 bg-green-600 hover:bg-green-700 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
                        <ExternalLink size={12} /> Open Groww Login
                      </a>
                    )}
                  </div>
                  {loginUrl && (
                    <form onSubmit={handleExchangeToken} className="flex gap-2">
                      <input type="text" value={requestToken}
                        onChange={e => setRequestToken(e.target.value)}
                        placeholder="Paste auth_code from Groww redirect URL"
                        className="flex-1 bg-gray-800 border border-gray-700 text-white rounded-lg px-3 py-1.5 text-xs focus:outline-none focus:border-green-500"
                      />
                      <button type="submit" disabled={exchanging || !requestToken.trim()}
                        className="bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white text-xs px-3 py-1.5 rounded-lg transition-colors">
                        {exchanging ? 'Exchanging...' : 'Get Access Token'}
                      </button>
                    </form>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Trading Mode */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Trading Mode</label>
            <div className="space-y-2">
              {TRADE_MODES.map(mode => (
                <label key={mode.value}
                  className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${form.trade_mode === mode.value ? 'border-blue-500 bg-blue-900/20' : 'border-gray-700 bg-gray-800 hover:border-gray-600'}`}>
                  <input type="radio" name="trade_mode" value={mode.value}
                    checked={form.trade_mode === mode.value}
                    onChange={e => setForm(f => ({ ...f, trade_mode: e.target.value }))}
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
            <select value={form.default_product}
              onChange={e => setForm(f => ({ ...f, default_product: e.target.value }))}
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
            {isBrokerConnectable && (
              <button type="button" onClick={handleTest} disabled={testing}
                className="flex items-center gap-2 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 text-white font-medium px-4 py-2.5 rounded-lg text-sm transition-colors">
                <RefreshCw size={14} className={testing ? 'animate-spin' : ''} />
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
            )}
          </div>

          {/* Zerodha setup guide */}
          {isZerodha && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 text-xs text-gray-400 space-y-2">
              <p className="font-medium text-gray-300">How to get Zerodha Kite API credentials:</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Log in to <a href="https://developers.kite.trade" target="_blank" rel="noopener noreferrer" className="text-blue-400 underline">developers.kite.trade</a></li>
                <li>Create a new app → copy the <strong className="text-white">API Key</strong> and <strong className="text-white">API Secret</strong></li>
                <li>Set your app's redirect URL to any URL you control (e.g. http://localhost/)</li>
                <li>Enter your API key and secret above, then use "Get Login URL" to authenticate</li>
                <li>After login, copy the <code className="text-green-400">request_token</code> from the redirect URL and exchange it for an access token</li>
              </ol>
              <p className="text-yellow-400/80 mt-2">⚠️ The access token expires at midnight IST and must be refreshed daily.</p>
            </div>
          )}

          {/* Groww setup guide */}
          {isGroww && (
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 text-xs text-gray-400 space-y-2">
              <p className="font-medium text-gray-300">How to get Groww Developer API credentials:</p>
              <ol className="list-decimal list-inside space-y-1">
                <li>Visit <a href="https://groww.in/open-api" target="_blank" rel="noopener noreferrer" className="text-green-400 underline">groww.in/open-api</a> and register your app</li>
                <li>Copy your <strong className="text-white">Client ID</strong> (use as API Key) and <strong className="text-white">Client Secret</strong></li>
                <li>Set your app's redirect URL in the Groww developer console</li>
                <li>Enter your Client ID and Client Secret above, then use "Get Login URL" to authorize</li>
                <li>After authorization, copy the <code className="text-green-400">auth_code</code> from the redirect URL and exchange it for an access token</li>
              </ol>
              <p className="text-yellow-400/80 mt-2">
                ℹ️ Historical data for Groww uses the NSE India public API (no separate Groww historical data API is needed).
              </p>
            </div>
          )}
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
          {!serverState.connected ? (
            <div className="text-center py-10 text-gray-500 text-sm">
              <WifiOff size={32} className="mx-auto mb-3 opacity-40" />
              Broker not connected. Complete the authentication above.
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
            <button onClick={loadPositions} className="text-gray-400 hover:text-white"><RefreshCw size={14} /></button>
          </div>
          {!serverState.connected ? (
            <div className="text-center py-10 text-gray-500 text-sm"><WifiOff size={32} className="mx-auto mb-3 opacity-40" />Broker not connected.</div>
          ) : positions ? (
            <pre className="bg-gray-800 rounded-lg p-4 text-xs text-gray-300 overflow-auto max-h-96">{JSON.stringify(positions, null, 2)}</pre>
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
            <button onClick={loadBrokerOrders} className="text-gray-400 hover:text-white"><RefreshCw size={14} /></button>
          </div>
          {!serverState.connected ? (
            <div className="text-center py-10 text-gray-500 text-sm"><WifiOff size={32} className="mx-auto mb-3 opacity-40" />Broker not connected.</div>
          ) : brokerOrders ? (
            <pre className="bg-gray-800 rounded-lg p-4 text-xs text-gray-300 overflow-auto max-h-96">{JSON.stringify(brokerOrders, null, 2)}</pre>
          ) : (
            <div className="text-center py-6 text-gray-500 text-sm">Click refresh to load orders</div>
          )}
        </div>
      )}
    </div>
  );
}

