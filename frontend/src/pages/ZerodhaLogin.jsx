import { useState } from 'react';
import { Key, ExternalLink, CheckCircle, ArrowRight, RefreshCw, TrendingUp } from 'lucide-react';
import toast from 'react-hot-toast';

/**
 * ZerodhaLogin
 *
 * A clean, full-screen login page for completing the Zerodha Kite Connect
 * token flow.  Displayed when the broker is set to Zerodha but the daily
 * access token has not yet been obtained.
 *
 * Props:
 *   apiKeySet      {boolean} - whether api_key is already saved
 *   onSaveCredentials({ api_key, api_secret }) - save key+secret then proceed
 *   onGetLoginUrl  {() => Promise<string>}    - get the Kite login URL
 *   onExchangeToken{(token: string) => Promise} - exchange request_token to access_token
 *   onDone         {() => void}               - called on successful token exchange
 */
export default function ZerodhaLogin({
  apiKeySet,
  onSaveCredentials,
  onGetLoginUrl,
  onExchangeToken,
  onDone,
}) {
  // Step state: 1=credentials, 2=login-url, 3=token
  const [step, setStep] = useState(apiKeySet ? 2 : 1);
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [loginUrl, setLoginUrl] = useState('');
  const [requestToken, setRequestToken] = useState('');
  const [loading, setLoading] = useState(false);

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
      onDone();
    } catch (err) {
      toast.error('Token exchange failed: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  }

  const steps = [
    { num: 1, label: 'API Credentials' },
    { num: 2, label: 'Login with Zerodha' },
    { num: 3, label: 'Paste Token' },
  ];

  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center px-4">
      {/* Logo */}
      <div className="flex items-center gap-3 mb-8">
        <div className="w-10 h-10 bg-green-600 rounded-xl flex items-center justify-center">
          <TrendingUp size={20} className="text-white" />
        </div>
        <div>
          <h1 className="text-white font-bold text-xl">AlgoPlatform</h1>
          <p className="text-gray-400 text-xs">Zerodha Kite Connect - Daily Login</p>
        </div>
      </div>

      {/* Step indicators */}
      <div className="flex items-center gap-2 mb-8">
        {steps.map((s, i) => (
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
            {i < steps.length - 1 && (
              <ArrowRight size={14} className="text-gray-600 mx-1" />
            )}
          </div>
        ))}
      </div>

      {/* Card */}
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-8 w-full max-w-md shadow-2xl">

        {/* Step 1: Enter API Key & Secret */}
        {step === 1 && (
          <>
            <div className="flex items-center gap-2 mb-6">
              <Key size={18} className="text-green-400" />
              <h2 className="text-white font-semibold text-lg">Enter Kite API Credentials</h2>
            </div>
            <p className="text-gray-400 text-sm mb-5">
              Get your API Key and API Secret from{' '}
              <a
                href="https://developers.kite.trade"
                target="_blank"
                rel="noreferrer"
                className="text-green-400 hover:underline"
              >
                developers.kite.trade
              </a>
              .
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
            <div className="flex items-center gap-2 mb-6">
              <ExternalLink size={18} className="text-green-400" />
              <h2 className="text-white font-semibold text-lg">Login with Zerodha</h2>
            </div>
            <p className="text-gray-400 text-sm mb-6">
              Click the button below to open the Zerodha login page. After logging in
              you will be redirected to your app's callback URL with a{' '}
              <code className="bg-gray-800 text-green-400 px-1 rounded">request_token</code>{' '}
              parameter in the URL.
            </p>
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-3 text-xs text-gray-400 mb-6 space-y-1">
              <p className="font-medium text-gray-300">What to do after login:</p>
              <p>1. Copy the <code className="text-green-400">request_token</code> value from the redirect URL</p>
              <p>2. Come back here and paste it in the next step</p>
              <p className="text-gray-500">
                Example URL: <span className="text-gray-400 break-all">https://your-app.com/callback?request_token=<span className="text-green-400">XXXXXXXX</span>&action=login&status=success</span>
              </p>
            </div>
            <div className="space-y-3">
              <button
                onClick={handleGetLoginUrl}
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-green-600 hover:bg-green-500 text-white font-semibold py-2.5 rounded-lg text-sm transition-colors disabled:opacity-50"
              >
                {loading ? (
                  <RefreshCw size={14} className="animate-spin" />
                ) : (
                  <ExternalLink size={14} />
                )}
                {loading ? 'Generating URL…' : 'Open Zerodha Login'}
              </button>
              <button
                onClick={() => setStep(3)}
                className="w-full text-gray-400 hover:text-white text-sm py-2 transition-colors"
              >
                I already have the request_token →
              </button>
            </div>
          </>
        )}

        {/* Step 3: Paste request_token */}
        {step === 3 && (
          <>
            <div className="flex items-center gap-2 mb-6">
              <Key size={18} className="text-green-400" />
              <h2 className="text-white font-semibold text-lg">Paste Request Token</h2>
            </div>

            {loginUrl && (
              <div className="bg-gray-800 border border-green-800/50 rounded-lg p-3 mb-4">
                <p className="text-xs text-gray-400 mb-1">Login URL (open in browser):</p>
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
              After logging in, copy the <code className="bg-gray-800 text-green-400 px-1 rounded">request_token</code> value from the redirect URL and paste it below.
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

      <p className="text-gray-600 text-xs mt-6 text-center">
        The access token is valid until midnight IST. You need to re-login each trading day.
      </p>
    </div>
  );
}
