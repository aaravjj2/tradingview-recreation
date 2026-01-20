/**
 * Autopilot Dashboard Component
 * Main dashboard showing status, portfolio, and controls
 */

import React, { useEffect, useCallback } from 'react';
import { useAutopilotStore } from '../store';
import { AutopilotThinkLog } from './AutopilotThinkLog';

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(value);
};

const formatPercent = (value: number): string => {
  return `${(value * 100).toFixed(2)}%`;
};

interface StatusBadgeProps {
  state: string;
  killSwitch: boolean;
}

const StatusBadge: React.FC<StatusBadgeProps> = ({ state, killSwitch }) => {
  if (killSwitch) {
    return (
      <span className="px-3 py-1 text-sm font-bold bg-red-600 text-white rounded-full animate-pulse">
        🛑 KILL SWITCH ACTIVE
      </span>
    );
  }

  const colors: Record<string, string> = {
    idle: 'bg-gray-500',
    running: 'bg-green-500',
    paused: 'bg-yellow-500',
    error: 'bg-red-500',
  };

  const safeState = state || 'idle';

  return (
    <span className={`px-3 py-1 text-sm font-semibold text-white rounded-full ${colors[safeState] || colors.idle}`}>
      {safeState.toUpperCase()}
    </span>
  );
};

const PaperModeBanner: React.FC = () => (
  <div
    className="w-full bg-amber-500 text-black text-center py-2 font-bold text-lg"
    data-testid="paper-mode-banner"
  >
    📄 PAPER TRADING MODE - NO REAL MONEY AT RISK
  </div>
);

interface PortfolioCardProps {
  title: string;
  value: string;
  subtitle?: string;
  trend?: 'up' | 'down' | 'neutral';
}

const PortfolioCard: React.FC<PortfolioCardProps> = ({ title, value, subtitle, trend }) => {
  const trendColors = {
    up: 'text-green-400',
    down: 'text-red-400',
    neutral: 'text-gray-400',
  };

  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700" data-testid={`portfolio-card-${title.toLowerCase().replace(/\s/g, '-')}`}>
      <h3 className="text-gray-400 text-sm font-medium">{title}</h3>
      <p className={`text-2xl font-bold mt-1 ${trend ? trendColors[trend] : 'text-white'}`}>
        {value}
      </p>
      {subtitle && <p className="text-gray-500 text-xs mt-1">{subtitle}</p>}
    </div>
  );
};

export const AutopilotDashboard: React.FC = () => {
  const {
    config,
    status,
    portfolio,
    isLoading,
    error,
    killSwitchPending,
    fetchConfig,
    fetchStatus,
    fetchPositions,
    triggerRun,
    activateKillSwitch,
    deactivateKillSwitch,
    pause,
    resume,
    clearError,
    connect,
    disconnect,
    connectionStatus,
  } = useAutopilotStore();

  useEffect(() => {
    connect();
    return () => disconnect();
  }, [connect, disconnect]);

  useEffect(() => {
    fetchConfig();
    fetchStatus();
    fetchPositions('open');

    // Poll status every 30 seconds
    const interval = setInterval(() => {
      fetchStatus();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchConfig, fetchStatus, fetchPositions]);

  const handleRunCycle = useCallback(async () => {
    await triggerRun(true);
    await fetchPositions('open');
  }, [triggerRun, fetchPositions]);

  const handleKillSwitch = useCallback(async () => {
    if (status?.kill_switch) {
      await deactivateKillSwitch();
    } else {
      await activateKillSwitch(true);
    }
  }, [status, activateKillSwitch, deactivateKillSwitch]);

  const handlePauseResume = useCallback(async () => {
    if (status?.state === 'paused') {
      await resume();
    } else {
      await pause();
    }
  }, [status, pause, resume]);

  const pnl = portfolio?.total_pnl ?? 0;
  const pnlTrend = pnl > 0 ? 'up' : pnl < 0 ? 'down' : 'neutral';
  const equity = (config?.paper_equity ?? 1000) + pnl;

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white" data-testid="autopilot-dashboard">
      <PaperModeBanner />

      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <h1 className="text-2xl font-bold">🤖 AI Options Autopilot</h1>
          {status && <StatusBadge state={status.state} killSwitch={status.kill_switch} />}
          <div className={`px-2 py-1 rounded-full text-xs font-bold ${connectionStatus === 'CONNECTED' ? 'bg-green-900 text-green-200 border border-green-700' :
              connectionStatus === 'CONNECTING' ? 'bg-yellow-900 text-yellow-200 border border-yellow-700 animate-pulse' :
                'bg-red-900 text-red-200 border border-red-700'
            }`}>
            WS: {connectionStatus}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handlePauseResume}
            disabled={isLoading || status?.kill_switch}
            className="px-4 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:bg-gray-600 rounded font-medium transition-colors"
            data-testid="pause-resume-btn"
          >
            {status?.state === 'paused' ? '▶️ Resume' : '⏸️ Pause'}
          </button>

          <button
            onClick={handleRunCycle}
            disabled={isLoading || status?.kill_switch}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded font-medium transition-colors"
            data-testid="run-cycle-btn"
          >
            {isLoading ? '⏳ Running...' : '🔄 Run Cycle'}
          </button>

          <button
            onClick={handleKillSwitch}
            disabled={killSwitchPending}
            className={`px-4 py-2 rounded font-medium transition-colors ${status?.kill_switch
              ? 'bg-green-600 hover:bg-green-700'
              : 'bg-red-600 hover:bg-red-700'
              }`}
            data-testid="kill-switch-btn"
          >
            {status?.kill_switch ? '✅ Deactivate Kill Switch' : '🛑 Kill Switch'}
          </button>
        </div>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-900 text-red-200 p-3 flex items-center justify-between" data-testid="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={clearError} className="text-red-400 hover:text-white">✕</button>
        </div>
      )}

      {/* Portfolio Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4 p-4">
        <PortfolioCard
          title="Paper Equity"
          value={formatCurrency(equity)}
          subtitle={`Started: ${formatCurrency(config?.paper_equity ?? 1000)}`}
        />
        <PortfolioCard
          title="Total P&L"
          value={formatCurrency(pnl)}
          trend={pnlTrend}
          subtitle={formatPercent(pnl / (config?.paper_equity ?? 1000))}
        />
        <PortfolioCard
          title="Unrealized P&L"
          value={formatCurrency(portfolio?.unrealized_pnl ?? 0)}
          trend={(portfolio?.unrealized_pnl ?? 0) >= 0 ? 'up' : 'down'}
        />
        <PortfolioCard
          title="Realized P&L"
          value={formatCurrency(portfolio?.realized_pnl ?? 0)}
          trend={(portfolio?.realized_pnl ?? 0) >= 0 ? 'up' : 'down'}
        />
        <PortfolioCard
          title="Open Positions"
          value={`${portfolio?.open_positions ?? 0} / ${config?.risk_limits?.max_open_positions ?? 10}`}
        />
        <PortfolioCard
          title="Total Risk"
          value={formatCurrency(portfolio?.total_risk ?? 0)}
          subtitle={`Max: ${formatCurrency(config?.risk_limits?.max_total_risk ?? 400)}`}
        />
      </div>

      {/* Greeks Summary */}
      {portfolio && (
        <div className="px-4 pb-4">
          <h2 className="text-lg font-semibold mb-2">Portfolio Greeks</h2>
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-gray-800 rounded p-3 text-center">
              <span className="text-gray-400 text-sm">Delta</span>
              <p className="text-xl font-mono">{portfolio.net_delta?.toFixed(2) ?? '0.00'}</p>
            </div>
            <div className="bg-gray-800 rounded p-3 text-center">
              <span className="text-gray-400 text-sm">Gamma</span>
              <p className="text-xl font-mono">{portfolio.net_gamma?.toFixed(4) ?? '0.0000'}</p>
            </div>
            <div className="bg-gray-800 rounded p-3 text-center">
              <span className="text-gray-400 text-sm">Theta</span>
              <p className="text-xl font-mono">{portfolio.net_theta?.toFixed(2) ?? '0.00'}</p>
            </div>
            <div className="bg-gray-800 rounded p-3 text-center">
              <span className="text-gray-400 text-sm">Vega</span>
              <p className="text-xl font-mono">{portfolio.net_vega?.toFixed(2) ?? '0.00'}</p>
            </div>
          </div>
        </div>
      )}

      {/* Mode & Config Info */}
      <div className="px-4 pb-4">
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h2 className="text-lg font-semibold mb-2">Configuration</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-gray-400">Mode:</span>
              <span className="ml-2 font-medium text-blue-400">{config?.mode ?? 'auto'}</span>
            </div>
            <div>
              <span className="text-gray-400">LLM:</span>
              <span className="ml-2 font-medium">{config?.llm_enabled ? '✅ Enabled' : '❌ Disabled'}</span>
            </div>
            <div>
              <span className="text-gray-400">Templates:</span>
              <span className="ml-2 font-medium">{config?.allowed_templates?.length ?? 5} active</span>
            </div>
            <div>
              <span className="text-gray-400">Last Cycle:</span>
              <span className="ml-2 font-medium">{status?.last_cycle_at ?? 'Never'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Quick Stats */}
      {status && (
        <div className="px-4 pb-4">
          <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
            <h2 className="text-lg font-semibold mb-2">Session Stats</h2>
            <div className="grid grid-cols-3 md:grid-cols-6 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Cycles:</span>
                <span className="ml-2 font-bold">{status.cycles_completed}</span>
              </div>
              <div>
                <span className="text-gray-400">Trades:</span>
                <span className="ml-2 font-bold">{status.trades_executed}</span>
              </div>
              <div>
                <span className="text-gray-400">Win Rate:</span>
                <span className={`ml-2 font-bold ${status.win_rate >= 0.5 ? 'text-green-400' : 'text-red-400'}`}>
                  {formatPercent(status.win_rate)}
                </span>
              </div>
              <div>
                <span className="text-gray-400">Avg Win:</span>
                <span className="ml-2 font-bold text-green-400">{formatCurrency(status.avg_win)}</span>
              </div>
              <div>
                <span className="text-gray-400">Avg Loss:</span>
                <span className="ml-2 font-bold text-red-400">{formatCurrency(status.avg_loss)}</span>
              </div>
              <div>
                <span className="text-gray-400">Sharpe:</span>
                <span className="ml-2 font-bold">{status.sharpe_ratio?.toFixed(2) ?? 'N/A'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Think Engine Log */}
      <div className="px-4 pb-4">
        <AutopilotThinkLog />
      </div>
    </div>
  );
};

export default AutopilotDashboard;
