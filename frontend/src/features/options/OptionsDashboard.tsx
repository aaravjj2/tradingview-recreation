/**
 * Options Feature Main Dashboard Component
 */

import React, { useEffect, useState } from 'react';
import { useOptionsStore } from './store';
import {
  IVAnalyticsPanel,
  PutCallRatioPanel,
  PayoffChart,
  StrategyMetrics,
  PositionGreeksPanel,
} from './components';
import { optionsApi } from './api';
import type { StrategyAnalysis } from './types';

interface OptionsDashboardProps {
  symbol?: string;
  className?: string;
}

export const OptionsDashboard: React.FC<OptionsDashboardProps> = ({
  symbol: initialSymbol,
  className = '',
}) => {
  const {
    symbol,
    fetchAll,
    chain,
    selectedExpiration,
    setSelectedExpiration,
  } = useOptionsStore();

  const [inputSymbol, setInputSymbol] = useState(initialSymbol || '');
  const [strategy, setStrategy] = useState<StrategyAnalysis | null>(null);
  const [strategyLoading, setStrategyLoading] = useState(false);

  // Load data when initial symbol provided
  useEffect(() => {
    if (initialSymbol && initialSymbol !== symbol) {
      setInputSymbol(initialSymbol);
      fetchAll(initialSymbol);
    }
  }, [initialSymbol]);

  const handleSymbolSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputSymbol.trim()) {
      fetchAll(inputSymbol.trim());
    }
  };

  const handleBuildIronCondor = async () => {
    if (!chain || !chain.underlyingPrice) return;
    
    setStrategyLoading(true);
    try {
      const price = chain.underlyingPrice;
      const result = await optionsApi.buildIronCondor({
        underlyingPrice: price,
        putLongStrike: Math.round(price * 0.90),
        putLongPremium: 1.0,
        putShortStrike: Math.round(price * 0.95),
        putShortPremium: 2.0,
        callShortStrike: Math.round(price * 1.05),
        callShortPremium: 2.0,
        callLongStrike: Math.round(price * 1.10),
        callLongPremium: 1.0,
        expirationDays: 30,
      });
      setStrategy(result);
    } catch (error) {
      console.error('Failed to build iron condor:', error);
    } finally {
      setStrategyLoading(false);
    }
  };

  const handleBuildStraddle = async () => {
    if (!chain || !chain.underlyingPrice) return;
    
    setStrategyLoading(true);
    try {
      const price = chain.underlyingPrice;
      const result = await optionsApi.buildStraddle({
        underlyingPrice: price,
        strike: Math.round(price),
        callPremium: price * 0.04,
        putPremium: price * 0.04,
        expirationDays: 30,
        isLong: true,
      });
      setStrategy(result);
    } catch (error) {
      console.error('Failed to build straddle:', error);
    } finally {
      setStrategyLoading(false);
    }
  };

  return (
    <div className={`bg-gray-900 text-white p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-bold">Options Analytics</h2>
        <form onSubmit={handleSymbolSubmit} className="flex gap-2">
          <input
            type="text"
            value={inputSymbol}
            onChange={(e) => setInputSymbol(e.target.value.toUpperCase())}
            placeholder="Symbol (e.g., AAPL)"
            className="bg-gray-800 border border-gray-600 rounded px-3 py-1 text-sm w-32"
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-700 px-3 py-1 rounded text-sm"
          >
            Load
          </button>
        </form>
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* IV Analytics */}
        <IVAnalyticsPanel />

        {/* Put/Call Ratio */}
        <PutCallRatioPanel />

        {/* Quick Actions */}
        <div className="bg-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">Quick Strategies</h3>
          <div className="space-y-2">
            <button
              onClick={handleBuildIronCondor}
              disabled={!chain || strategyLoading}
              className="w-full bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 
                         px-3 py-2 rounded text-sm transition"
            >
              Build Iron Condor
            </button>
            <button
              onClick={handleBuildStraddle}
              disabled={!chain || strategyLoading}
              className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-600 
                         px-3 py-2 rounded text-sm transition"
            >
              Build Long Straddle
            </button>
          </div>
          
          {chain && (
            <div className="mt-4 pt-3 border-t border-gray-700">
              <div className="text-xs text-gray-400 space-y-1">
                <div>Underlying: ${chain.underlyingPrice.toFixed(2)}</div>
                <div>Contracts: {chain.totalContracts}</div>
                <div>Expirations: {chain.expirations.length}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Strategy Analysis Section */}
      {strategy && (
        <div className="mt-4 bg-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold text-gray-300 mb-3">
            {strategy.name} Analysis
          </h3>
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div>
              <PayoffChart strategy={strategy} width={400} height={250} />
              <div className="mt-2 flex gap-4 text-xs">
                <span className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-green-500"></span> Expiration
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-blue-500"></span> Theoretical
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-3 h-0.5 bg-yellow-500"></span> Breakeven
                </span>
              </div>
            </div>
            
            <div className="space-y-4">
              <StrategyMetrics strategy={strategy} />
              <PositionGreeksPanel strategy={strategy} />
            </div>
          </div>
        </div>
      )}

      {/* Expiration Selector */}
      {chain && chain.expirations.length > 0 && (
        <div className="mt-4">
          <label className="text-xs text-gray-400 block mb-1">Expiration</label>
          <select
            value={selectedExpiration || ''}
            onChange={(e) => setSelectedExpiration(e.target.value)}
            className="bg-gray-800 border border-gray-600 rounded px-3 py-1 text-sm"
          >
            {chain.expirations.map(exp => (
              <option key={exp} value={exp}>{exp}</option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};

export default OptionsDashboard;
