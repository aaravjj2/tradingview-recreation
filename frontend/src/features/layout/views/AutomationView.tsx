import { useState } from 'react';
import { Bot, Play, Square, Shield, AlertTriangle, DollarSign, TrendingUp, Activity } from 'lucide-react';
import { Button } from '../../../ui/Button';
import { Badge } from '../../../ui/Badge';
import { Panel } from '../../../ui/Panel';
import { cn } from '../../../ui/utils';

interface BudgetConfig {
    maxTotalNotional: number;
    maxDailySpend: number;
    maxPerTrade: number;
    maxConcurrentPositions: number;
    maxLeverage: number;
    hardDrawdownStop: number;
}

interface AutopilotStatus {
    armed: boolean;
    mode: 'paper' | 'live';
    currentSpentToday: number;
    activeStrategies: string[];
    killSwitchTriggered: boolean;
}

export function AutomationView() {
    const [status, setStatus] = useState<AutopilotStatus>({
        armed: false,
        mode: 'paper',
        currentSpentToday: 0,
        activeStrategies: [],
        killSwitchTriggered: false,
    });

    const [budget, setBudget] = useState<BudgetConfig>({
        maxTotalNotional: 10000,
        maxDailySpend: 1000,
        maxPerTrade: 500,
        maxConcurrentPositions: 5,
        maxLeverage: 1,
        hardDrawdownStop: 0.1,
    });

    const [confirmArm, setConfirmArm] = useState(false);

    const handleArmPaper = () => {
        setStatus(prev => ({ ...prev, armed: true, mode: 'paper' }));
        setConfirmArm(false);
    };

    const handleArmLive = () => {
        if (!confirmArm) {
            setConfirmArm(true);
            return;
        }
        setStatus(prev => ({ ...prev, armed: true, mode: 'live' }));
        setConfirmArm(false);
    };

    const handleDisarm = () => {
        setStatus(prev => ({ ...prev, armed: false }));
        setConfirmArm(false);
    };

    const handleKillSwitch = () => {
        setStatus(prev => ({ ...prev, armed: false, killSwitchTriggered: true, activeStrategies: [] }));
    };

    return (
        <div className="h-full overflow-auto bg-background p-6">
            <div className="max-w-5xl mx-auto space-y-6">
                {/* Header */}
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Bot className="text-brand" size={28} />
                        <div>
                            <h1 className="text-2xl font-bold text-text">Automation</h1>
                            <p className="text-sm text-text-secondary">One-click Autopilot with budget controls</p>
                        </div>
                    </div>
                    <Badge variant={status.armed ? (status.mode === 'live' ? 'error' : 'success') : 'default'}>
                        {status.armed ? `${status.mode.toUpperCase()} ARMED` : 'DISARMED'}
                    </Badge>
                </div>

                {/* Kill Switch Warning */}
                {status.killSwitchTriggered && (
                    <Panel className="bg-red-500/10 border-red-500">
                        <div className="flex items-center gap-3 text-red-500">
                            <AlertTriangle size={24} />
                            <div>
                                <p className="font-semibold">Kill Switch Triggered</p>
                                <p className="text-sm opacity-80">All automation has been stopped. Review incidents before restarting.</p>
                            </div>
                        </div>
                    </Panel>
                )}

                {/* Main Controls */}
                <div className="grid grid-cols-3 gap-4">
                    <Panel className="p-6">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Play size={18} className="text-green-500" />
                            Run Autopilot (Paper)
                        </h3>
                        <p className="text-sm text-text-secondary mb-4">
                            Start automated trading in paper mode. No real money at risk.
                        </p>
                        <Button
                            variant={status.armed && status.mode === 'paper' ? 'secondary' : 'primary'}
                            className="w-full"
                            onClick={status.armed ? handleDisarm : handleArmPaper}
                            disabled={status.killSwitchTriggered}
                        >
                            {status.armed && status.mode === 'paper' ? 'Stop Paper Trading' : 'Start Paper Trading'}
                        </Button>
                    </Panel>

                    <Panel className="p-6 border-orange-500/30">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Shield size={18} className="text-orange-500" />
                            Arm Live Autopilot
                        </h3>
                        <p className="text-sm text-text-secondary mb-4">
                            {confirmArm 
                                ? '⚠️ Click again to confirm LIVE trading activation.'
                                : 'Enable real trading. Requires two-step confirmation.'}
                        </p>
                        <Button
                            variant={confirmArm ? 'danger' : 'secondary'}
                            className={cn("w-full", confirmArm && "animate-pulse")}
                            onClick={status.armed && status.mode === 'live' ? handleDisarm : handleArmLive}
                            disabled={status.killSwitchTriggered}
                        >
                            {status.armed && status.mode === 'live' 
                                ? 'Disarm Live Trading' 
                                : confirmArm 
                                    ? 'CONFIRM LIVE TRADING' 
                                    : 'Arm Live Trading'}
                        </Button>
                    </Panel>

                    <Panel className="p-6 border-red-500/30">
                        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                            <Square size={18} className="text-red-500" />
                            Emergency Kill Switch
                        </h3>
                        <p className="text-sm text-text-secondary mb-4">
                            Immediately stop all automation and optionally close positions.
                        </p>
                        <Button
                            variant="danger"
                            className="w-full"
                            onClick={handleKillSwitch}
                            disabled={!status.armed}
                        >
                            Kill All Automation
                        </Button>
                    </Panel>
                </div>

                {/* Budget Controls */}
                <Panel className="p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <DollarSign size={18} className="text-brand" />
                        Budget & Risk Controls
                    </h3>
                    <div className="grid grid-cols-3 gap-6">
                        <div>
                            <label className="text-sm text-text-secondary">Max Total Notional</label>
                            <div className="flex items-center gap-2 mt-1">
                                <span className="text-text-muted">$</span>
                                <input
                                    type="number"
                                    value={budget.maxTotalNotional}
                                    onChange={e => setBudget(prev => ({ ...prev, maxTotalNotional: Number(e.target.value) }))}
                                    className="bg-element-bg border border-border rounded px-3 py-2 text-text w-full"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="text-sm text-text-secondary">Max Daily Spend</label>
                            <div className="flex items-center gap-2 mt-1">
                                <span className="text-text-muted">$</span>
                                <input
                                    type="number"
                                    value={budget.maxDailySpend}
                                    onChange={e => setBudget(prev => ({ ...prev, maxDailySpend: Number(e.target.value) }))}
                                    className="bg-element-bg border border-border rounded px-3 py-2 text-text w-full"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="text-sm text-text-secondary">Max Per Trade</label>
                            <div className="flex items-center gap-2 mt-1">
                                <span className="text-text-muted">$</span>
                                <input
                                    type="number"
                                    value={budget.maxPerTrade}
                                    onChange={e => setBudget(prev => ({ ...prev, maxPerTrade: Number(e.target.value) }))}
                                    className="bg-element-bg border border-border rounded px-3 py-2 text-text w-full"
                                />
                            </div>
                        </div>
                        <div>
                            <label className="text-sm text-text-secondary">Max Concurrent Positions</label>
                            <input
                                type="number"
                                value={budget.maxConcurrentPositions}
                                onChange={e => setBudget(prev => ({ ...prev, maxConcurrentPositions: Number(e.target.value) }))}
                                className="bg-element-bg border border-border rounded px-3 py-2 text-text w-full mt-1"
                            />
                        </div>
                        <div>
                            <label className="text-sm text-text-secondary">Max Leverage</label>
                            <input
                                type="number"
                                value={budget.maxLeverage}
                                onChange={e => setBudget(prev => ({ ...prev, maxLeverage: Number(e.target.value) }))}
                                className="bg-element-bg border border-border rounded px-3 py-2 text-text w-full mt-1"
                                step="0.5"
                                min="1"
                                max="4"
                            />
                        </div>
                        <div>
                            <label className="text-sm text-text-secondary">Hard Drawdown Stop (%)</label>
                            <input
                                type="number"
                                value={budget.hardDrawdownStop * 100}
                                onChange={e => setBudget(prev => ({ ...prev, hardDrawdownStop: Number(e.target.value) / 100 }))}
                                className="bg-element-bg border border-border rounded px-3 py-2 text-text w-full mt-1"
                                step="1"
                                min="1"
                                max="50"
                            />
                        </div>
                    </div>

                    {/* Spend Progress */}
                    <div className="mt-6 pt-6 border-t border-border">
                        <div className="flex items-center justify-between mb-2">
                            <span className="text-sm text-text-secondary">Today's Spend</span>
                            <span className="text-sm font-mono">${status.currentSpentToday.toLocaleString()} / ${budget.maxDailySpend.toLocaleString()}</span>
                        </div>
                        <div className="h-2 bg-element-bg rounded-full overflow-hidden">
                            <div 
                                className={cn(
                                    "h-full rounded-full transition-all",
                                    status.currentSpentToday / budget.maxDailySpend > 0.8 ? "bg-red-500" :
                                    status.currentSpentToday / budget.maxDailySpend > 0.5 ? "bg-yellow-500" : "bg-green-500"
                                )}
                                style={{ width: `${Math.min(100, (status.currentSpentToday / budget.maxDailySpend) * 100)}%` }}
                            />
                        </div>
                    </div>
                </Panel>

                {/* Active Strategies */}
                <Panel className="p-6">
                    <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                        <TrendingUp size={18} className="text-brand" />
                        Active Strategies
                    </h3>
                    {status.activeStrategies.length === 0 ? (
                        <div className="text-center py-8 text-text-secondary">
                            <Activity size={32} className="mx-auto mb-2 opacity-50" />
                            <p>No active strategies</p>
                            <p className="text-sm">Arm autopilot to activate strategies</p>
                        </div>
                    ) : (
                        <div className="space-y-2">
                            {status.activeStrategies.map(strat => (
                                <div key={strat} className="flex items-center justify-between p-3 bg-element-bg rounded">
                                    <span>{strat}</span>
                                    <Badge variant="success">Running</Badge>
                                </div>
                            ))}
                        </div>
                    )}
                </Panel>

                {/* Strategy Selection Note */}
                <Panel className="p-4 bg-blue-500/10 border-blue-500/30">
                    <p className="text-sm text-blue-400">
                        <strong>Strategy Selection:</strong> Autopilot selects strategies based on long-horizon backtests, 
                        robustness suite results, and current regime classification. It will never "invent a strategy and trade immediately."
                    </p>
                </Panel>
            </div>
        </div>
    );
}
