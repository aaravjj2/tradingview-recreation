/**
 * Option Chain Tile - Options pricing grid
 */

import { useState } from 'react';
import { cn } from '../../../ui/utils';

interface TileProps {
    tileId: string;
    onClose: () => void;
    onMaximize: () => void;
    isMaximized: boolean;
}

interface OptionContract {
    strike: number;
    callBid: number;
    callAsk: number;
    callVolume: number;
    callOI: number;
    putBid: number;
    putAsk: number;
    putVolume: number;
    putOI: number;
    callIV: number;
    putIV: number;
}

const underlyingPrice = 178.52;

const MOCK_CHAIN: OptionContract[] = [
    { strike: 165, callBid: 14.20, callAsk: 14.40, callVolume: 1234, callOI: 5678, putBid: 0.45, putAsk: 0.50, putVolume: 567, putOI: 2345, callIV: 0.28, putIV: 0.32 },
    { strike: 170, callBid: 9.80, callAsk: 10.00, callVolume: 2345, callOI: 8901, putBid: 1.10, putAsk: 1.20, putVolume: 890, putOI: 3456, callIV: 0.26, putIV: 0.30 },
    { strike: 175, callBid: 5.90, callAsk: 6.10, callVolume: 4567, callOI: 12345, putBid: 2.30, putAsk: 2.45, putVolume: 1234, putOI: 5678, callIV: 0.24, putIV: 0.28 },
    { strike: 180, callBid: 3.20, callAsk: 3.40, callVolume: 5678, callOI: 15678, putBid: 4.50, putAsk: 4.70, putVolume: 2345, putOI: 7890, callIV: 0.23, putIV: 0.26 },
    { strike: 185, callBid: 1.45, callAsk: 1.55, callVolume: 3456, callOI: 10234, putBid: 7.80, putAsk: 8.00, putVolume: 1567, putOI: 4567, callIV: 0.25, putIV: 0.27 },
    { strike: 190, callBid: 0.55, callAsk: 0.65, callVolume: 1234, callOI: 6789, putBid: 12.00, putAsk: 12.30, putVolume: 890, putOI: 3456, callIV: 0.28, putIV: 0.30 },
];

export function OptionChainTile({ tileId: _tileId, isMaximized: _isMaximized }: TileProps) {
    const [expiry, setExpiry] = useState('2024-01-19');

    return (
        <div className="h-full flex flex-col text-xs">
            {/* Expiry selector */}
            <div className="flex items-center gap-2 p-2 border-b border-border">
                <span className="text-text-muted">Expiry:</span>
                <select
                    value={expiry}
                    onChange={(e) => setExpiry(e.target.value)}
                    className="bg-element-bg text-text rounded px-2 py-1 border border-border"
                >
                    <option value="2024-01-19">Jan 19, 2024</option>
                    <option value="2024-01-26">Jan 26, 2024</option>
                    <option value="2024-02-16">Feb 16, 2024</option>
                </select>
                <span className="text-text-muted ml-auto">AAPL @ ${underlyingPrice}</span>
            </div>

            {/* Header */}
            <div className="grid grid-cols-9 gap-1 px-2 py-1 text-xxs text-text-muted border-b border-border bg-element-bg/50">
                <div className="text-center">Bid</div>
                <div className="text-center">Ask</div>
                <div className="text-center">Vol</div>
                <div className="text-center">IV</div>
                <div className="text-center font-semibold text-text">Strike</div>
                <div className="text-center">IV</div>
                <div className="text-center">Vol</div>
                <div className="text-center">Bid</div>
                <div className="text-center">Ask</div>
            </div>

            {/* Chain */}
            <div className="flex-1 overflow-y-auto">
                {MOCK_CHAIN.map((opt) => {
                    const isITMCall = opt.strike < underlyingPrice;
                    const isITMPut = opt.strike > underlyingPrice;
                    const isATM = Math.abs(opt.strike - underlyingPrice) < 2.5;

                    return (
                        <div
                            key={opt.strike}
                            className={cn(
                                "grid grid-cols-9 gap-1 px-2 py-1.5 border-b border-border/50 hover:bg-element-bg",
                                isATM && "bg-brand/10"
                            )}
                        >
                            {/* Calls */}
                            <div className={cn("text-center", isITMCall && "bg-green-500/10")}>{opt.callBid.toFixed(2)}</div>
                            <div className={cn("text-center", isITMCall && "bg-green-500/10")}>{opt.callAsk.toFixed(2)}</div>
                            <div className={cn("text-center text-text-muted", isITMCall && "bg-green-500/10")}>{opt.callVolume}</div>
                            <div className={cn("text-center text-text-muted", isITMCall && "bg-green-500/10")}>{(opt.callIV * 100).toFixed(0)}%</div>
                            
                            {/* Strike */}
                            <div className={cn(
                                "text-center font-semibold",
                                isATM ? "text-brand" : "text-text"
                            )}>
                                {opt.strike}
                            </div>
                            
                            {/* Puts */}
                            <div className={cn("text-center text-text-muted", isITMPut && "bg-red-500/10")}>{(opt.putIV * 100).toFixed(0)}%</div>
                            <div className={cn("text-center text-text-muted", isITMPut && "bg-red-500/10")}>{opt.putVolume}</div>
                            <div className={cn("text-center", isITMPut && "bg-red-500/10")}>{opt.putBid.toFixed(2)}</div>
                            <div className={cn("text-center", isITMPut && "bg-red-500/10")}>{opt.putAsk.toFixed(2)}</div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
