/**
 * Autopilot API Client
 */

import type {
  AutopilotConfig,
  AutopilotStatus,
  AutopilotPosition,
  PortfolioState,
  CycleResult,
  ActivityLogEntry,
  DailyReport,
} from './types';

const API_BASE = '/api/v1/autopilot';

async function fetchJSON<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }
  
  return response.json();
}

export const autopilotApi = {
  /**
   * Get current configuration
   */
  async getConfig(): Promise<{ config: AutopilotConfig; defaults: AutopilotConfig }> {
    return fetchJSON(`${API_BASE}/config`);
  },

  /**
   * Update configuration
   */
  async updateConfig(update: Partial<{
    paper_equity: number;
    mode: string;
    risk_limits: Partial<AutopilotConfig['risk_limits']>;
    allowed_templates: string[];
    forecast_influence: number;
    llm_enabled: boolean;
  }>): Promise<{ status: string; config: AutopilotConfig }> {
    return fetchJSON(`${API_BASE}/config`, {
      method: 'POST',
      body: JSON.stringify(update),
    });
  },

  /**
   * Trigger an autopilot run
   */
  async triggerRun(force = false): Promise<{ status: string; cycle: CycleResult }> {
    return fetchJSON(`${API_BASE}/run`, {
      method: 'POST',
      body: JSON.stringify({ force }),
    });
  },

  /**
   * Get current status
   */
  async getStatus(): Promise<AutopilotStatus> {
    return fetchJSON(`${API_BASE}/status`);
  },

  /**
   * Get proposals from last run
   */
  async getProposals(): Promise<{
    cycle_id: string;
    candidates_generated: number;
    candidates_by_template: Record<string, number>;
    selected_count: number;
    selection_method: string;
    timestamp: string;
  }> {
    return fetchJSON(`${API_BASE}/proposals`);
  },

  /**
   * Get positions
   */
  async getPositions(status?: 'open' | 'closed' | 'all'): Promise<{
    positions: AutopilotPosition[];
    count: number;
    portfolio: PortfolioState;
  }> {
    const url = status ? `${API_BASE}/positions?status=${status}` : `${API_BASE}/positions`;
    return fetchJSON(url);
  },

  /**
   * Get activity logs
   */
  async getLogs(options?: {
    limit?: number;
    event_type?: string;
    level?: string;
  }): Promise<{ logs: ActivityLogEntry[]; count: number }> {
    const params = new URLSearchParams();
    if (options?.limit) params.set('limit', options.limit.toString());
    if (options?.event_type) params.set('event_type', options.event_type);
    if (options?.level) params.set('level', options.level);
    
    const url = `${API_BASE}/logs?${params.toString()}`;
    return fetchJSON(url);
  },

  /**
   * Activate/deactivate kill switch
   */
  async setKillSwitch(activate: boolean, closeAll = false): Promise<{ status: string }> {
    return fetchJSON(`${API_BASE}/kill_switch`, {
      method: 'POST',
      body: JSON.stringify({ activate, close_all: closeAll }),
    });
  },

  /**
   * Get daily report
   */
  async getDailyReport(reportDate?: string): Promise<{ report: DailyReport; markdown: string }> {
    const url = reportDate 
      ? `${API_BASE}/report?report_date=${reportDate}`
      : `${API_BASE}/report`;
    return fetchJSON(url);
  },

  /**
   * Pause autopilot
   */
  async pause(): Promise<{ status: string }> {
    return fetchJSON(`${API_BASE}/pause`, { method: 'POST' });
  },

  /**
   * Resume autopilot
   */
  async resume(): Promise<{ status: string }> {
    return fetchJSON(`${API_BASE}/resume`, { method: 'POST' });
  },

  /**
   * Get broker metrics
   */
  async getBrokerMetrics(): Promise<{
    total_orders: number;
    filled_orders: number;
    rejected_orders: number;
    fill_rate: number;
    total_slippage: number;
  }> {
    return fetchJSON(`${API_BASE}/broker/metrics`);
  },

  /**
   * Get trading universe
   */
  async getUniverse(): Promise<{
    symbols: Array<{ symbol: string; sector: string; liquidity_tier: string }>;
    count: number;
  }> {
    return fetchJSON(`${API_BASE}/universe`);
  },
};
