import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
