// API client for trading system
// Supports switching between mock data and real backend

const BASE_URL = 'http://100.100.238.72:8000/api';
const USE_MOCK = false;

import { mockResearchPacks, mockPMPitches, mockCouncilDecision, mockTrades, mockPositions, mockAccounts } from '../lib/mockData';

const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

export const tradingApi = {
  // Research
  getResearch: async () => {
    if (USE_MOCK) {
      await delay(500);
      return mockResearchPacks;
    }
    const res = await fetch(`${BASE_URL}/research/current`);
    return res.json();
  },

  generateResearch: async () => {
    const res = await fetch(`${BASE_URL}/research/generate`, { method: 'POST' });
    return res.json();
  },

  verifyResearch: async (id) => {
    const res = await fetch(`${BASE_URL}/research/verify`, {
        method: 'POST',
        body: JSON.stringify({ id }),
        headers: { 'Content-Type': 'application/json' }
    });
    return res.json();
  },

  // PM Pitches
  getPitches: async () => {
    if (USE_MOCK) {
      await delay(500);
      return mockPMPitches;
    }
    const res = await fetch(`${BASE_URL}/pitches/current`);
    return res.json();
  },

  approvePitch: async (id) => {
    const res = await fetch(`${BASE_URL}/pitches/${id}/approve`, { method: 'POST' });
    return res.json();
  },

  // Council
  getCouncilDecision: async () => {
    if (USE_MOCK) {
      await delay(500);
      return mockCouncilDecision;
    }
    const res = await fetch(`${BASE_URL}/council/current`);
    return res.json();
  },

  // Trades
  getPendingTrades: async () => {
    if (USE_MOCK) {
        await delay(300);
        return mockTrades.filter(t => t.status === 'pending');
    }
    const res = await fetch(`${BASE_URL}/trades/pending`);
    return res.json();
  },

  executeTrades: async (tradeIds) => {
    const res = await fetch(`${BASE_URL}/trades/execute`, {
        method: 'POST',
        body: JSON.stringify({ tradeIds }),
        headers: { 'Content-Type': 'application/json' }
    });
    return res.json();
  },

  // Monitor
  getPositions: async () => {
    if (USE_MOCK) {
        await delay(300);
        return mockPositions;
    }
    const res = await fetch(`${BASE_URL}/positions`);
    return res.json();
  },
  
  getAccounts: async () => {
    if (USE_MOCK) {
        await delay(300);
        return mockAccounts;
    }
    const res = await fetch(`${BASE_URL}/accounts`);
    return res.json();
  }
};