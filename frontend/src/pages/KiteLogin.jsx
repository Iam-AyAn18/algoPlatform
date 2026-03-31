import { useState } from 'react';
import {
  Key, ExternalLink, CheckCircle, ArrowRight, RefreshCw,
  BookOpen, Info, AlertCircle, ChevronDown, ChevronUp,
} from 'lucide-react';
import toast from 'react-hot-toast';

/**
 * KiteLogin
 *
 * A dedicated page for Zerodha Kite API login with step-by-step instructions
 * and an interactive login form.
 *
 * Props:
 *   brokerState            {object}  - current broker settings from the server
 *   onSaveCredentials      {fn}      - save api_key + api_secret
 *   onGetLoginUrl          {fn}      - get the Kite login URL
 *   onExchangeToken        {fn}      - exchange request_token for access_token
 *   onDone                 {fn}      - callback on successful token exchange
 */
export default function KiteLogin({
  brokerState,
  onSaveCredentials,
  onGetLoginUrl,
  onExchangeToken,
  onDone,
}) {
  const apiKeySet = brokerState?.api_key_masked ? brokerState.api_key_masked.length > 0 : false;
  const isConnected = brokerState?.connected && brokerState?.broker_name === 'zerodha';

  // Step state: 1=credentials, 2=login-url, 3=token
  const [step, setStep] = useState(apiKeySet ? 2 : 1);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [loginUrl, setLoginUrl] = useState('');
  const [requestToken, setRequestToken] = useState('');
  const [loading, setLoading] = useState(false);
  const [showFullGuide, setShowFullGuide] = useState(false);

  async function handleSaveCredentials(e) {
    e.preventDefault();
    if (!apiKey.trim() || !apiSecret.trim()) {
      toast.error('Please enter both API Key and API Secret');
      return;
    }
    setLoading(true);
    try {
      await onSaveCredentials({ api_key: apiKey.trim(), api_secret: apiSecret.trim() });
      toast.success('Credentials saved');
      setStep(2);
    } catch (err) {
      toast.error('Failed to save: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }

  async function handleGetLoginUrl() {
    setLoading(true);
    try {
      const url = await onGetLoginUrl();
      setLoginUrl(url);
      window.open(url, '_blank', 'noreferrer');
      setStep(3);
    } catch (err) {
      toast.error('Failed to get login URL: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }

  async function handleExchangeToken(e) {
    e.preventDefault();
    if (!requestToken.trim()) {
      toast.error('Please paste the request_token from the redirect URL');
      return;
    }
    setLoading(true);
    try {
      await onExchangeToken(requestToken.trim());
      toast.success('✅ Zerodha connected! Access token saved.');
      if (onDone) onDone();
    } catch (err) {
      toast.error('Token exchange failed: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }

  const loginSteps = [
    { num: 1, label: 'API Credentials' },
    { num: 2, label: 'Login with Zerodha' },
    { num: 3, label: 'Paste Token' },
  ];

  return (
    <div className="space-y-6">

      {/* Page header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-green-600 rounded-xl flex items-center justify-center shrink-0">
          <Key size={20} className="text-white" />
        </div>
        <div>
          <h2 className="text-white font-bold text-xl">Kite API Login</h2>
          <p className="text-gray-400 text-sm">Connect AlgoPlatform to Zerodha using the Kite Connect API</p>
        </div>
        {isConnected && (
          <span className="ml-auto flex items-center gap-1.5 text-green-400 text-sm bg-green-900/30 border border-green-800/50 rounded-full px-3 py-1">
            <CheckCircle size={14} />
            Connected
          </span>
        )}
      </div>

      {/* ─── Instructions Section ─── */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden">
        <button
          onClick={() => setShowFullGuide(v => !v)}
          className="w-full flex items-center justify-between px-6 py-4 hover:bg-gray-800/50 transition-colors"
        >
          <div className="flex items-center gap-2">
            <BookOpen size={16} className="text-green-400" />
            <span className="text-white font-semibold">How to use the Kite API – Instructions</span>
          </div>
          {showFullGuide
            ? <ChevronUp size={16} className="text-gray-400" />
            : <ChevronDown size={16} className="text-gray-400" />}
        </button>

        {/* Always-visible quick overview */}
        <div className="px-6 pb-5 space-y-4 border-t border-gray-800">
          <p className="text-gray-400 text-sm pt-4">
            <strong className="text-white">Kite Connect</strong> is Zerodha's official trading API. It lets
            AlgoPlatform fetch live quotes, place orders, and view your portfolio directly from your Zerodha account.
            Follow the steps below to connect.
          </p>

          {/* Quick-step visual guide */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {[
              {
                icon: <Key size={18} className="text-green-400" />,
                title: '1. Create a Kite App',
                body: 'Visit developers.kite.trade, sign in with your Zerodha account, and create a new app to get your API Key and API Secret.',
              },
              {
                icon: <ExternalLink size={18} className="text-blue-400" />,
                title: '2. Authorize Daily Login',
                body: 'Each trading day you must open the Kite login URL in your browser, log in, and copy the request_token from the redirect URL.',
              },
              {
                icon: <CheckCircle size={18} className="text-purple-400" />,
                title: '3. Exchange the Token',
                body: 'Paste the request_token here. AlgoPlatform exchanges it for a session access_token (valid until midnight IST).',
              },
            ].map(card => (
              <div key={card.title} className="bg-gray-800 rounded-xl p-4 space-y-2">
                {card.icon}
                <p className="text-white text-sm font-semibold">{card.title}</p>
                <p className="text-gray-400 text-xs leading-relaxed">{card.body}</p>
              </div>
            ))}
          </div>

          {/* Expandable detailed guide */}
          {showFullGuide && (
            <div className="space-y-5 pt-2">
              <hr className="border-gray-700" />

              {/* Step A */}
              <div className="space-y-2">
                <h4 className="text-white font-semibold text-sm flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-green-600 flex items-center justify-center text-xs">A</span>
                  Create a Kite Connect App
                </h4>
                <ol className="list-decimal list-inside space-y-1.5 text-gray-400 text-sm pl-2">
                  <li>
                    Go to{' '}
                    <a
                      href="https://developers.kite.trade"
                      target="_blank"
                      rel="noreferrer"
                      className="text-green-400 hover:underline"
                    >
                      developers.kite.trade
                    </a>{' '}
                    and sign in with your Zerodha account.
                  </li>
                  <li>Click <strong className="text-gray-200">Create new app</strong> (or <strong className="text-gray-200">My Apps</strong>).</li>
                  <li>Fill in the app name, Redirect URL (can be <code className="bg-gray-800 text-green-400 px-1 rounded">https://127.0.0.1/</code> for testing), and description.</li>
                  <li>After saving, copy the <strong className="text-gray-200">API Key</strong> and <strong className="text-gray-200">API Secret</strong> shown on the app page.</li>
                </ol>
              </div>

              {/* Step B */}
              <div className="space-y-2">
                <h4 className="text-white font-semibold text-sm flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-blue-600 flex items-center justify-center text-xs">B</span>
                  Save Credentials in AlgoPlatform
                </h4>
                <ol className="list-decimal list-inside space-y-1.5 text-gray-400 text-sm pl-2">
                  <li>In the <strong className="text-gray-200">Login Form</strong> below, enter your API Key and API Secret.</li>
                  <li>Click <strong className="text-gray-200">Save &amp; Continue</strong>. The credentials are stored securely on the local server.</li>
                </ol>
              </div>

              {/* Step C */}
              <div className="space-y-2">
                <h4 className="text-white font-semibold text-sm flex items-center gap-2">
                  <span className="w-5 h-5 rounded-full bg-purple-600 flex items-center justify-center text-xs">C</span>
                  Daily Login (every trading day)
                </h4>
                <ol className="list-decimal list-inside space-y-1.5 text-gray-400 text-sm pl-2">
                  <li>Click <strong className="text-gray-200">Open Zerodha Login</strong>. A new browser tab opens with the Kite login page.</li>
                  <li>Enter your Zerodha credentials (username + password + 2FA PIN).</li>
                  <li>
                    After login, Zerodha redirects you to your Redirect URL. Look at the address bar —
                    copy the <code className="bg-gray-800 text-green-400 px-1 rounded">request_token</code> value from the URL.
                  </li>
                  <li>
                    Paste the token into the <strong className="text-gray-200">Request Token</strong> field below and click{' '}
                    <strong className="text-gray-200">Connect to Zerodha</strong>.
                  </li>
                  <li>
                    AlgoPlatform exchanges the token for an <strong className="text-gray-200">access_token</strong>{' '}
                    (valid until midnight IST). After midnight, repeat this step.
                  </li>
                </ol>
              </div>

              {/* Notes */}
              <div className="bg-yellow-900/20 border border-yellow-700/40 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-yellow-400 text-sm font-semibold">
                  <AlertCircle size={14} />
                  Important notes
                </div>
                <ul className="list-disc list-inside space-y-1 text-gray-400 text-xs pl-1">
                  <li>The access token <strong className="text-gray-300">expires every day at midnight IST</strong>. You must re-login each trading day.</li>
                  <li>Keep your API Secret private — never share it publicly.</li>
                  <li>You can use <strong className="text-gray-300">Analysis mode</strong> (paper trading) without a Zerodha login.</li>
                  <li>
                    Kite Connect API documentation:{' '}
                    <a
                      href="https://kite.trade/docs/connect/v3/"
                      target="_blank"
                      rel="noreferrer"
                      className="text-green-400 hover:underline"
                    >
                      kite.trade/docs/connect/v3
                    </a>
                  </li>
                </ul>
              </div>

              {/* URL format example */}
              <div className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-2">
                <div className="flex items-center gap-2 text-gray-300 text-sm font-semibold">
                  <Info size={14} className="text-blue-400" />
                  How to extract the request_token from the redirect URL
                </div>
                <p className="text-gray-400 text-xs">
                  After Zerodha login, you'll land on a URL like:
                </p>
                <div className="bg-gray-900 rounded-lg px-3 py-2 text-xs font-mono break-all">
                  <span className="text-gray-500">https://your-redirect-url.com/callback?</span>
                  <span className="text-white">request_token=</span>
                  <span className="text-green-400">AbCdEfGh12345678</span>
                  <span className="text-gray-500">&amp;action=login&amp;status=success</span>
                </div>
                <p className="text-gray-400 text-xs">
                  Copy only the value after <code className="text-green-400">request_token=</code> — in this
                  example it is <code className="text-green-400">AbCdEfGh12345678</code>.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ─── Login Form ─── */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
        <div className="flex items-center gap-2 mb-5">
          <Key size={16} className="text-green-400" />
          <h3 className="text-white font-semibold">Login Form</h3>
          {isConnected && (
            <span className="text-xs text-green-400 bg-green-900/30 border border-green-800/50 rounded-full px-2 py-0.5 ml-1">
              Active session — re-login to refresh token
            </span>
          )}
        </div>

        {/* Step indicators */}
        <div className="flex items-center gap-2 mb-6">
          {loginSteps.map((s, i) => (
            <div key={s.num} className="flex items-center gap-2">
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2
                  ${step > s.num
                    ? 'bg-green-600 border-green-600 text-white'
                    : step === s.num
                      ? 'bg-gray-900 border-green-500 text-green-400'
                      : 'bg-gray-900 border-gray-700 text-gray-500'
                  }`}
              >
                {step > s.num ? <CheckCircle size={14} /> : s.num}
              </div>
              <span
                className={`text-xs font-medium hidden sm:block
                  ${step === s.num ? 'text-white' : 'text-gray-500'}`}
              >
                {s.label}
              </span>
              {i < loginSteps.length - 1 && (
                <ArrowRight size={14} className="text-gray-600 mx-1" />
              )}
            </div>
          ))}
        </div>

        <div className="max-w-md">

          {/* Step 1: Enter API Key & Secret */}
          {step === 1 && (
            <>
              <p className="text-gray-400 text-sm mb-4">
                Enter your Kite Connect <strong className="text-gray-200">API Key</strong> and{' '}
                <strong className="text-gray-200">API Secret</strong> from{' '}
                <a
                  href="https://developers.kite.trade"
                  target="_blank"
                  rel="noreferrer"
                  className="text-green-400 hover:underline"
                >
                  developers.kite.trade
                </a>.
              </p>
              <form onSubmit={handleSaveCredentials} className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">API Key</label>
                  <input
                    type="text"
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    placeholder="e.g. abcdefgh12345678"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                  />
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">API Secret</label>
                  <input
                    type="password"
                    value={apiSecret}
                    onChange={e => setApiSecret(e.target.value)}
                    placeholder="Your Kite API secret"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-green-600 hover:bg-green-500 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors disabled:opacity-50"
                >
                  {loading ? 'Saving…' : 'Save & Continue'}
                </button>
              </form>
            </>
          )}

          {/* Step 2: Open Login URL */}
          {step === 2 && (
            <>
              <p className="text-gray-400 text-sm mb-4">
                Click the button below to open the Zerodha login page. After logging in you will be redirected to
                your app's callback URL with a{' '}
                <code className="bg-gray-800 text-green-400 px-1 rounded">request_token</code> parameter in the URL.
              </p>
              <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-400 mb-5 space-y-1">
                <p className="font-medium text-gray-300">What to do after login:</p>
                <p>1. Copy the <code className="text-green-400">request_token</code> value from the redirect URL</p>
                <p>2. Come back here and paste it in the next step</p>
                <p className="text-gray-500 break-all">
                  Example:{' '}
                  <span className="text-gray-400">
                    …?request_token=<span className="text-green-400">XXXXXXXX</span>&amp;action=login&amp;status=success
                  </span>
                </p>
              </div>
              <div className="space-y-3">
                <button
                  onClick={handleGetLoginUrl}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors disabled:opacity-50"
                >
                  {loading ? <RefreshCw size={14} className="animate-spin" /> : <ExternalLink size={14} />}
                  {loading ? 'Generating URL…' : 'Open Zerodha Login'}
                </button>
                <button
                  onClick={() => setStep(3)}
                  className="w-full text-gray-400 hover:text-white text-sm py-2 transition-colors"
                >
                  I already have the request_token →
                </button>
                <button
                  onClick={() => setStep(1)}
                  className="w-full text-gray-500 hover:text-gray-300 text-xs py-1 transition-colors"
                >
                  ← Change API credentials
                </button>
              </div>
            </>
          )}

          {/* Step 3: Paste request_token */}
          {step === 3 && (
            <>
              {loginUrl && (
                <div className="bg-gray-800 border border-green-800/50 rounded-lg p-3 mb-4">
                  <p className="text-xs text-gray-400 mb-1">Login URL (opens in new tab):</p>
                  <a
                    href={loginUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-green-400 hover:underline text-xs break-all flex items-center gap-1"
                  >
                    <ExternalLink size={11} /> {loginUrl}
                  </a>
                </div>
              )}
              <p className="text-gray-400 text-sm mb-4">
                After logging in, copy the{' '}
                <code className="bg-gray-800 text-green-400 px-1 rounded">request_token</code> from the redirect
                URL and paste it below.
              </p>
              <form onSubmit={handleExchangeToken} className="space-y-4">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Request Token</label>
                  <input
                    type="text"
                    value={requestToken}
                    onChange={e => setRequestToken(e.target.value)}
                    placeholder="Paste request_token here"
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-green-500"
                  />
                </div>
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors disabled:opacity-50"
                >
                  {loading ? <RefreshCw size={14} className="animate-spin" /> : <CheckCircle size={14} />}
                  {loading ? 'Connecting…' : 'Connect to Zerodha'}
                </button>
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="w-full text-gray-500 hover:text-gray-300 text-xs py-1 transition-colors"
                >
                  ← Back to login step
                </button>
              </form>
            </>
          )}
        </div>
      </div>

      <p className="text-gray-600 text-xs text-center">
        The access token is valid until midnight IST. Re-login each trading day using the form above.
      </p>
    </div>
  );
}
