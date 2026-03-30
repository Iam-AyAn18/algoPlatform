import axios from 'axios';

// Use VITE_API_URL if set; otherwise use relative paths so Vite's dev-server
// proxy (vite.config.js) forwards them to localhost:8000.
const BASE_URL = import.meta.env.VITE_API_URL || '';

const api = axios.create({ baseURL: BASE_URL });

// Market Data
export const getQuote = (symbol, exchange = 'NSE') =>
  api.get(`/market/quote/${symbol}`, { params: { exchange } }).then(r => r.data);

export const getBulkQuotes = (symbols, exchange = 'NSE') =>
  api.get('/market/quotes', { params: { symbols: symbols.join(','), exchange } }).then(r => r.data);

export const getNifty50 = () =>
  api.get('/market/nifty50').then(r => r.data);

export const getHistorical = (symbol, exchange = 'NSE', period = '1y', interval = '1d') =>
  api.get(`/market/historical/${symbol}`, { params: { exchange, period, interval } }).then(r => r.data);

// Orders
export const placeOrder = (order) =>
  api.post('/orders/', order).then(r => r.data);

export const listOrders = (limit = 50) =>
  api.get('/orders/', { params: { limit } }).then(r => r.data);

export const cancelOrder = (id) =>
  api.delete(`/orders/${id}`);

// Portfolio
export const getPortfolio = () =>
  api.get('/portfolio/').then(r => r.data);

export const resetPortfolio = () =>
  api.post('/portfolio/reset').then(r => r.data);

// Watchlist
export const getWatchlist = () =>
  api.get('/watchlist/').then(r => r.data);

export const addToWatchlist = (symbol, exchange = 'NSE') =>
  api.post('/watchlist/', { symbol, exchange }).then(r => r.data);

export const removeFromWatchlist = (symbol) =>
  api.delete(`/watchlist/${symbol}`);

// Strategies
export const listStrategies = () =>
  api.get('/strategies/').then(r => r.data);

export const getSignal = (symbol, exchange = 'NSE', strategy = 'MA_CROSSOVER', params = {}) =>
  api.get(`/strategies/signal/${symbol}`, { params: { exchange, strategy, ...params } }).then(r => r.data);

// Backtest
export const runBacktest = (req) =>
  api.post('/backtest/', req).then(r => r.data);

// Broker Settings – direct broker API integration (no intermediate server needed)
export const getBrokerSettings = () =>
  api.get('/broker/settings').then(r => r.data);

export const updateBrokerSettings = (settings) =>
  api.put('/broker/settings', settings).then(r => r.data);

export const testBrokerConnection = () =>
  api.post('/broker/test-connection').then(r => r.data);

// Zerodha Kite login flow
export const getBrokerLoginUrl = () =>
  api.get('/broker/login-url').then(r => r.data);

export const exchangeRequestToken = (requestToken) =>
  api.post('/broker/exchange-token', null, { params: { request_token: requestToken } }).then(r => r.data);

export const getBrokerFunds = () =>
  api.get('/broker/funds').then(r => r.data);

export const getBrokerPositions = () =>
  api.get('/broker/positions').then(r => r.data);

export const getBrokerOrders = () =>
  api.get('/broker/orders').then(r => r.data);

// Trading mode (Analysis vs Live Trading)
export const setTradingMode = (isLiveTrading) =>
  api.post('/broker/trading-mode', null, { params: { is_live_trading: isLiveTrading } }).then(r => r.data);

// Algo Trading – Webhook & Action Center
export const sendWebhookSignal = (payload) =>
  api.post('/algo/webhook', payload).then(r => r.data);

export const listWebhookSignals = (limit = 50) =>
  api.get('/algo/webhook/signals', { params: { limit } }).then(r => r.data);

export const listActionCenterOrders = () =>
  api.get('/algo/action-center').then(r => r.data);

export const approveOrder = (orderId) =>
  api.post(`/algo/action-center/${orderId}/approve`).then(r => r.data);

export const rejectOrder = (orderId) =>
  api.post(`/algo/action-center/${orderId}/reject`).then(r => r.data);

export const approveAllOrders = () =>
  api.post('/algo/action-center/approve-all').then(r => r.data);

