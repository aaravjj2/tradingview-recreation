import { useState, useEffect } from 'react';
import { Panel, Group as PanelGroup, Separator as PanelResizeHandle } from 'react-resizable-panels';
import { OptionsChain } from '../../options/OptionsChain';
import { IVSkewChart } from '../../options/IVSkewChart';
import { IVTermStructure } from '../../options/IVTermStructure';
import { StrategyBuilder } from '../../options/StrategyBuilder';
import { FundamentalsPanel } from '../../fundamentals/FundamentalsPanel';
import { IndicatorManager } from '../../indicators/IndicatorManager';
import { useAppStore } from '../../../state/appStore';
import { useOptionsStore } from '../../options/store';

type OptionsTab = 'chain' | 'iv-skew' | 'iv-term' | 'strategy' | 'fundamentals';

export function OptionsView() {
  const { symbol: appSymbol } = useAppStore();
  const {
    fetchAll,
    chain,
    selectedExpiration,
    setSelectedExpiration,
    chainLoading
  } = useOptionsStore();

  const [activeTab, setActiveTab] = useState<OptionsTab>('chain');
  const [indicatorManagerOpen, setIndicatorManagerOpen] = useState(false);
  const [, setIndicators] = useState<unknown[]>([]);

  // Fetch all data when app-wide symbol changes
  useEffect(() => {
    if (appSymbol) {
      fetchAll(appSymbol);
    }
  }, [appSymbol, fetchAll]);

  const handleIndicatorUpdate = (newIndicators: any[]) => {
    setIndicators(newIndicators);
  };

  const tabs = [
    { id: 'chain' as const, label: 'Options Chain' },
    { id: 'iv-skew' as const, label: 'IV Skew' },
    { id: 'iv-term' as const, label: 'IV Term Structure' },
    { id: 'strategy' as const, label: 'Strategy Builder' },
    { id: 'fundamentals' as const, label: 'Fundamentals' },
  ];

  return (
    <div className="h-full w-full flex flex-col bg-background">
      {/* Header with tabs */}
      <div className="flex items-center justify-between border-b border-border px-4 py-2 bg-panel-bg">
        <div className="flex items-center gap-4">
          <h1 className="text-lg font-semibold text-text">Options Analytics - {appSymbol}</h1>

          {/* Expiration selector */}
          {chain && chain.expirations.length > 0 && (activeTab === 'chain' || activeTab === 'iv-skew' || activeTab === 'iv-term') && (
            <select
              value={selectedExpiration || ''}
              onChange={(e) => setSelectedExpiration(e.target.value)}
              className="px-3 py-1.5 bg-element-bg border border-border rounded text-sm text-text focus:outline-none focus:ring-1 focus:ring-brand"
            >
              {chain.expirations.map(exp => (
                <option key={exp} value={exp}>{exp}</option>
              ))}
            </select>
          )}

          {chainLoading && <span className="text-xs text-text-muted animate-pulse">Loading...</span>}
        </div>

        {/* Indicator Manager Toggle */}
        <button
          onClick={() => setIndicatorManagerOpen(!indicatorManagerOpen)}
          className="px-3 py-1.5 bg-brand/10 hover:bg-brand/20 text-brand rounded text-sm font-medium transition-colors"
        >
          {indicatorManagerOpen ? 'Hide Indicators' : 'Show Indicators'}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-border px-4 bg-panel-bg">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${activeTab === tab.id
              ? 'border-brand text-brand'
              : 'border-transparent text-text-secondary hover:text-text hover:border-border'
              }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Main content area */}
      <div className="flex-1 overflow-hidden">
        <PanelGroup orientation="horizontal">
          <Panel defaultSize={indicatorManagerOpen ? 75 : 100} minSize={50}>
            <div className="h-full overflow-auto">
              {activeTab === 'chain' && (
                <OptionsChain
                  symbol={appSymbol}
                  expiration={selectedExpiration || ''}
                  underlyingPrice={chain?.underlyingPrice}
                />
              )}

              {activeTab === 'iv-skew' && (
                <IVSkewChart
                  symbol={appSymbol}
                  expiration={selectedExpiration || ''}
                  underlyingPrice={chain?.underlyingPrice}
                />
              )}

              {activeTab === 'iv-term' && (
                <IVTermStructure symbol={appSymbol} />
              )}

              {activeTab === 'strategy' && (
                <StrategyBuilder
                  symbol={appSymbol}
                  underlyingPrice={chain?.underlyingPrice || 0}
                />
              )}

              {activeTab === 'fundamentals' && (
                <FundamentalsPanel symbol={appSymbol} />
              )}
            </div>
          </Panel>

          {indicatorManagerOpen && (
            <>
              <PanelResizeHandle className="w-1 bg-border hover:bg-brand transition-colors cursor-col-resize" />
              <Panel defaultSize={25} minSize={15} maxSize={40}>
                <IndicatorManager
                  symbol={appSymbol}
                  onIndicatorUpdate={handleIndicatorUpdate}
                />
              </Panel>
            </>
          )}
        </PanelGroup>
      </div>
    </div>
  );
}
