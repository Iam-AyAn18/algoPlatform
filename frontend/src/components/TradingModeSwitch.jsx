import { useState } from 'react';
import { ShieldCheck, Zap, AlertTriangle } from 'lucide-react';
import { setTradingMode } from '../api';
import toast from 'react-hot-toast';

/**
 * TradingModeSwitch
 *
 * Displays the current trading mode (Analysis / Live Trading) and lets the
 * user toggle between them.  Switching TO Live Trading requires an explicit
 * confirmation to prevent accidental activation.
 *
 * Props:
 *   isLiveTrading  {boolean}  – current mode from broker settings
 *   onChange       {(bool)=>} – called with the new value after a successful toggle
 */
export default function TradingModeSwitch({ isLiveTrading, onChange }) {
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);

  async function applyMode(enable) {
    setLoading(true);
    try {
      await setTradingMode(enable);
      onChange(enable);
      toast.success(
        enable
          ? '⚠️ Live Trading mode activated – real orders will be sent to your broker'
          : '🛡️ Switched to Analysis mode – no real orders will be sent'
      );
    } catch (err) {
      toast.error('Failed to switch mode: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
      setShowConfirm(false);
    }
  }

  function handleClick() {
    if (!isLiveTrading) {
      // Switching to Live → show confirmation dialog first
      setShowConfirm(true);
    } else {
      // Switching back to Analysis → no confirmation needed
      applyMode(false);
    }
  }

  return (
    <>
      {/* Mode badge / toggle button */}
      <button
        onClick={handleClick}
        disabled={loading}
        title={
          isLiveTrading
            ? 'Live Trading active – click to switch to Analysis mode'
            : 'Analysis mode active – click to enable Live Trading'
        }
        className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-colors
          ${isLiveTrading
            ? 'bg-red-900/60 border-red-600 text-red-300 hover:bg-red-800/70'
            : 'bg-green-900/40 border-green-700 text-green-300 hover:bg-green-800/50'
          } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        {isLiveTrading ? (
          <Zap size={11} className="fill-current" />
        ) : (
          <ShieldCheck size={11} />
        )}
        {isLiveTrading ? 'Live Trading' : 'Analysis'}
      </button>

      {/* Confirmation dialog for enabling Live Trading */}
      {showConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="bg-gray-900 border border-red-700 rounded-xl p-6 max-w-sm w-full mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full bg-red-900/60 flex items-center justify-center flex-shrink-0">
                <AlertTriangle size={20} className="text-red-400" />
              </div>
              <div>
                <h2 className="text-white font-bold text-base">Enable Live Trading?</h2>
                <p className="text-gray-400 text-xs mt-0.5">Real orders will be sent to your broker</p>
              </div>
            </div>

            <div className="bg-red-950/50 border border-red-800/60 rounded-lg p-3 mb-5 text-xs text-red-300 space-y-1">
              <p>⚠️ <strong>Real money is at risk.</strong></p>
              <p>• Orders placed while Live Trading is active go directly to your Zerodha account.</p>
              <p>• Make sure your broker connection and strategy settings are correct before proceeding.</p>
            </div>

            <div className="flex gap-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="flex-1 px-4 py-2 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 text-sm font-medium transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => applyMode(true)}
                disabled={loading}
                className="flex-1 px-4 py-2 rounded-lg bg-red-700 hover:bg-red-600 text-white text-sm font-bold transition-colors disabled:opacity-50"
              >
                {loading ? 'Activating…' : 'Yes, Enable Live Trading'}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
