/**
 * Centralized API client for backend integration.
 */

const API_BASE = 'http://localhost:8000/api/v1';

export interface ParityStatus {
    symbol: string;
    timeframe: string;
    count: number;
    hash: string;
    from_ms: number | null;
    to_ms: number | null;
}

export interface HealthResponse {
    status: 'healthy' | 'degraded' | 'unhealthy';
}

export interface StrategyResponse {
    id: string;
    name: string;
    strategy_type: string;
    symbol: string;
    status: string;
    params: Record<string, unknown>;
    created_at: string;
    started_at: string | null;
    metrics: Record<string, unknown>;
}

export interface Position {
    symbol: string;
    qty: number;
    avg_price: number;
    current_price: number;
    pnl?: number;
    unrealized_pnl?: number;
}

export interface Order {
    id: string;
    strategy_id?: string;
    symbol: string;
    side: 'BUY' | 'SELL';
    type: 'MARKET' | 'LIMIT' | 'STOP';
    qty: number;
    filled_qty: number;
    status: 'PENDING' | 'FILLED' | 'CANCELLED' | 'REJECTED' | 'OPEN';
    created_at: string;
}

export interface Alert {
    id: string;
    name?: string;
    symbol: string;
    condition: string;
    value: number;
    status: string;
    delivery: string[];
    throttle?: string;
    triggered?: number;
}

export const ApiClient = {
    // Health
    async checkHealth(): Promise<HealthResponse> {
        try {
            const res = await fetch(`http://localhost:8000/health`);
            if (!res.ok) return { status: 'unhealthy' };
            return { status: 'healthy' };
        } catch {
            return { status: 'unhealthy' };
        }
    },

    // Ingestion provider status
    async getProviderStatus(): Promise<{ provider: string | null; running: boolean }> {
        try {
            const res = await fetch(`http://localhost:8000/api/v1/ingest/provider-status`);
            if (!res.ok) return { provider: null, running: false };
            return res.json();
        } catch {
            return { provider: null, running: false };
        }
    },

    // Parity
    async getParityHash(symbol: string, timeframe: string): Promise<ParityStatus> {
        const res = await fetch(`${API_BASE}/parity/hash/${symbol}/${timeframe}`);
        if (!res.ok) throw new Error('Failed to fetch parity hash');
        return res.json();
    },

    async compareParity(symbol: string, timeframe: string, csvFile: File): Promise<{
        match: boolean;
        local_hash: string;
        reference_hash: string | null;
        local_count: number;
        reference_count: number;
        diffs: unknown[];
        message: string;
    }> {
        const formData = new FormData();
        formData.append('file', csvFile);

        const res = await fetch(`${API_BASE}/parity/compare/${symbol}/${timeframe}`, {
            method: 'POST',
            body: formData,
        });
        if (!res.ok) throw new Error('Failed to compare parity');
        return res.json();
    },

    // Strategies
    async listStrategies(): Promise<StrategyResponse[]> {
        const res = await fetch(`${API_BASE}/strategies`);
        if (!res.ok) throw new Error('Failed to list strategies');
        return res.json();
    },

    async createStrategy(data: {
        name: string;
        strategy_type: string;
        symbol: string;
        params?: Record<string, unknown>;
    }): Promise<StrategyResponse> {
        const res = await fetch(`${API_BASE}/strategies`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error('Failed to create strategy');
        return res.json();
    },

    async startStrategy(id: string): Promise<void> {
        const res = await fetch(`${API_BASE}/strategies/${id}/start`, { method: 'POST' });
        if (!res.ok) throw new Error('Failed to start strategy');
    },

    async stopStrategy(id: string): Promise<void> {
        const res = await fetch(`${API_BASE}/strategies/${id}/stop`, { method: 'POST' });
        if (!res.ok) throw new Error('Failed to stop strategy');
    },

    async deleteStrategy(id: string): Promise<void> {
        const res = await fetch(`${API_BASE}/strategies/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete strategy');
    },

    // Portfolio
    async getPositions(): Promise<Position[]> {
        const res = await fetch(`${API_BASE}/portfolio/positions`);
        if (!res.ok) return [];
        return res.json();
    },

    async getOrders(): Promise<Order[]> {
        const res = await fetch(`${API_BASE}/portfolio/orders`);
        if (!res.ok) return [];
        return res.json();
    },

    // Alerts
    async listAlerts(): Promise<Alert[]> {
        const res = await fetch(`${API_BASE}/alerts`);
        if (!res.ok) return [];
        return res.json();
    },

    async createAlert(data: {
        name?: string;
        symbol: string;
        condition: string;
        value: number;
        delivery: string[];
    }): Promise<Alert> {
        const res = await fetch(`${API_BASE}/alerts`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data),
        });
        if (!res.ok) throw new Error('Failed to create alert');
        return res.json();
    },

    async deleteAlert(id: string): Promise<void> {
        const res = await fetch(`${API_BASE}/alerts/${id}`, { method: 'DELETE' });
        if (!res.ok) throw new Error('Failed to delete alert');
    },
};
