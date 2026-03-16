import { useState } from 'react';
import { placeOrder } from '../api';
import toast from 'react-hot-toast';

export default function OrderPanel({ onOrderPlaced }) {
  const [form, setForm] = useState({
    symbol: '',
    exchange: 'NSE',
    side: 'BUY',
    order_type: 'MARKET',
    quantity: '',
    price: '',
    trigger_price: '',
    strategy: '',
  });
  const [loading, setLoading] = useState(false);

  const handleChange = e => setForm(f => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async e => {
    e.preventDefault();
    if (!form.symbol || !form.quantity) return toast.error('Symbol and quantity are required');
    if (form.order_type === 'SL' && !form.trigger_price) return toast.error('Trigger price is required for SL orders');
    setLoading(true);
    try {
      const payload = {
        symbol: form.symbol.toUpperCase(),
        exchange: form.exchange,
        side: form.side,
        order_type: form.order_type,
        quantity: parseInt(form.quantity),
        ...(form.order_type === 'LIMIT' && form.price ? { price: parseFloat(form.price) } : {}),
        ...(form.order_type === 'SL' && form.trigger_price ? { trigger_price: parseFloat(form.trigger_price) } : {}),
        ...(form.order_type === 'SL' && form.price ? { price: parseFloat(form.price) } : {}),
        ...(form.strategy ? { strategy: form.strategy } : {}),
      };
      const result = await placeOrder(payload);
      if (result.status === 'EXECUTED') {
        toast.success(`Order executed @ ₹${result.executed_price?.toLocaleString('en-IN')}`);
      } else if (result.status === 'REJECTED') {
        toast.error('Order rejected – insufficient funds or no position');
      } else {
        toast.success(`Order placed: ${result.status}`);
      }
      onOrderPlaced?.();
      setForm(f => ({ ...f, symbol: '', quantity: '', price: '', trigger_price: '' }));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to place order');
    } finally {
      setLoading(false);
    }
  };

  const inputCls = 'w-full bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-400 focus:outline-none focus:border-green-500';
  const labelCls = 'text-xs text-gray-400 mb-1 block';

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Symbol</label>
          <input name="symbol" value={form.symbol} onChange={handleChange}
            placeholder="RELIANCE" className={inputCls} />
        </div>
        <div>
          <label className={labelCls}>Exchange</label>
          <select name="exchange" value={form.exchange} onChange={handleChange} className={inputCls}>
            <option>NSE</option>
            <option>BSE</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Side</label>
          <div className="flex gap-2">
            {['BUY', 'SELL'].map(s => (
              <button key={s} type="button"
                onClick={() => setForm(f => ({ ...f, side: s }))}
                className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors
                  ${form.side === s
                    ? s === 'BUY' ? 'bg-green-600 text-white' : 'bg-red-600 text-white'
                    : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>
                {s}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className={labelCls}>Order Type</label>
          <select name="order_type" value={form.order_type} onChange={handleChange} className={inputCls}>
            <option value="MARKET">MARKET</option>
            <option value="LIMIT">LIMIT</option>
            <option value="SL">STOP-LOSS (SL)</option>
          </select>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className={labelCls}>Quantity</label>
          <input name="quantity" type="number" min="1" value={form.quantity}
            onChange={handleChange} placeholder="10" className={inputCls} />
        </div>
        {(form.order_type === 'LIMIT' || form.order_type === 'SL') && (
          <div>
            <label className={labelCls}>Limit Price (₹)</label>
            <input name="price" type="number" step="0.01" value={form.price}
              onChange={handleChange} placeholder="2500.00" className={inputCls} />
          </div>
        )}
      </div>

      {form.order_type === 'SL' && (
        <div>
          <label className={labelCls}>Trigger Price (₹) <span className="text-red-400">*</span></label>
          <input name="trigger_price" type="number" step="0.01" value={form.trigger_price}
            onChange={handleChange} placeholder="2480.00" className={inputCls} />
          <p className="text-xs text-gray-500 mt-1">
            {form.side === 'SELL'
              ? 'Order executes when price falls to this level'
              : 'Order executes when price rises to this level'}
          </p>
        </div>
      )}

      <div>
        <label className={labelCls}>Strategy Tag (optional)</label>
        <input name="strategy" value={form.strategy} onChange={handleChange}
          placeholder="MA_CROSSOVER" className={inputCls} />
      </div>

      <button type="submit" disabled={loading}
        className={`w-full py-3 rounded-xl font-semibold text-sm transition-all
          ${form.side === 'BUY'
            ? 'bg-green-600 hover:bg-green-500 text-white'
            : 'bg-red-600 hover:bg-red-500 text-white'}
          disabled:opacity-50 disabled:cursor-not-allowed`}>
        {loading ? 'Placing…' : `Place ${form.side} ${form.order_type} Order`}
      </button>
    </form>
  );
}
