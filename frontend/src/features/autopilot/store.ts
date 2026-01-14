/**
 * Autopilot Zustand Store
 */

import { create } from 'zustand';
import { immer } from 'zustand/middleware/immer';
import type {
  AutopilotConfig,
  AutopilotPosition,
  PortfolioState,
  CycleResult,
  ActivityLogEntry,
  DailyReport,
  AutopilotStatus,
} from './types';
import { autopilotApi } from './api';

interface AutopilotStore {
  // State
  config: AutopilotConfig | null;
  defaults: AutopilotConfig | null;
  status: AutopilotStatus | null;
  positions: AutopilotPosition[];
  portfolio: PortfolioState | null;
  logs: ActivityLogEntry[];
  lastCycle: CycleResult | null;
  dailyReport: DailyReport | null;
  reportMarkdown: string;
  
  // UI state
  isLoading: boolean;
  error: string | null;
  killSwitchPending: boolean;
  
  // Actions
  fetchConfig: () => Promise<void>;
  updateConfig: (update: Partial<AutopilotConfig>) => Promise<void>;
  fetchStatus: () => Promise<void>;
  fetchPositions: (status?: 'open' | 'closed' | 'all') => Promise<void>;
  fetchLogs: (options?: { limit?: number; event_type?: string }) => Promise<void>;
  triggerRun: (force?: boolean) => Promise<CycleResult | null>;
  activateKillSwitch: (closeAll?: boolean) => Promise<void>;
  deactivateKillSwitch: () => Promise<void>;
  pause: () => Promise<void>;
  resume: () => Promise<void>;
  fetchDailyReport: (date?: string) => Promise<void>;
  clearError: () => void;
}

export const useAutopilotStore = create<AutopilotStore>()(
  immer((set, get) => ({
    // Initial state
    config: null,
    defaults: null,
    status: null,
    positions: [],
    portfolio: null,
    logs: [],
    lastCycle: null,
    dailyReport: null,
    reportMarkdown: '',
    isLoading: false,
    error: null,
    killSwitchPending: false,

    fetchConfig: async () => {
      set((state) => { state.isLoading = true; state.error = null; });
      try {
        const { config, defaults } = await autopilotApi.getConfig();
        set((state) => {
          state.config = config;
          state.defaults = defaults;
          state.isLoading = false;
        });
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to fetch config';
          state.isLoading = false;
        });
      }
    },

    updateConfig: async (update) => {
      set((state) => { state.isLoading = true; state.error = null; });
      try {
        const { config } = await autopilotApi.updateConfig(update);
        set((state) => {
          state.config = config;
          state.isLoading = false;
        });
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to update config';
          state.isLoading = false;
        });
      }
    },

    fetchStatus: async () => {
      try {
        const status = await autopilotApi.getStatus();
        set((state) => { state.status = status; });
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to fetch status';
        });
      }
    },

    fetchPositions: async (status) => {
      set((state) => { state.isLoading = true; state.error = null; });
      try {
        const { positions, portfolio } = await autopilotApi.getPositions(status);
        set((state) => {
          state.positions = positions;
          state.portfolio = portfolio;
          state.isLoading = false;
        });
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to fetch positions';
          state.isLoading = false;
        });
      }
    },

    fetchLogs: async (options) => {
      set((state) => { state.isLoading = true; state.error = null; });
      try {
        const { logs } = await autopilotApi.getLogs(options);
        set((state) => {
          state.logs = logs;
          state.isLoading = false;
        });
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to fetch logs';
          state.isLoading = false;
        });
      }
    },

    triggerRun: async (force = false) => {
      set((state) => { state.isLoading = true; state.error = null; });
      try {
        const { cycle } = await autopilotApi.triggerRun(force);
        set((state) => {
          state.lastCycle = cycle;
          state.isLoading = false;
        });
        // Refresh positions after run
        get().fetchPositions('open');
        return cycle;
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to trigger run';
          state.isLoading = false;
        });
        return null;
      }
    },

    activateKillSwitch: async (closeAll = false) => {
      set((state) => { state.killSwitchPending = true; state.error = null; });
      try {
        await autopilotApi.setKillSwitch(true, closeAll);
        await get().fetchStatus();
        set((state) => { state.killSwitchPending = false; });
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to activate kill switch';
          state.killSwitchPending = false;
        });
      }
    },

    deactivateKillSwitch: async () => {
      set((state) => { state.killSwitchPending = true; state.error = null; });
      try {
        await autopilotApi.setKillSwitch(false);
        await get().fetchStatus();
        set((state) => { state.killSwitchPending = false; });
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to deactivate kill switch';
          state.killSwitchPending = false;
        });
      }
    },

    pause: async () => {
      try {
        await autopilotApi.pause();
        await get().fetchStatus();
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to pause';
        });
      }
    },

    resume: async () => {
      try {
        await autopilotApi.resume();
        await get().fetchStatus();
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to resume';
        });
      }
    },

    fetchDailyReport: async (date) => {
      set((state) => { state.isLoading = true; state.error = null; });
      try {
        const { report, markdown } = await autopilotApi.getDailyReport(date);
        set((state) => {
          state.dailyReport = report;
          state.reportMarkdown = markdown;
          state.isLoading = false;
        });
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : 'Failed to fetch report';
          state.isLoading = false;
        });
      }
    },

    clearError: () => {
      set((state) => { state.error = null; });
    },
  }))
);
