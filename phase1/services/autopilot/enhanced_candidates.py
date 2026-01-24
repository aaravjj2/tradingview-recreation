"""
Enhanced Candidate Generator

Integrates the Trading Intelligence Engine and Strategy Selection Matrix
to generate high-quality trade candidates with sophisticated factor analysis.

This module replaces the simple trend-based strategy selection with a
comprehensive multi-factor scoring model.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Any, Tuple
from datetime import date, datetime, timedelta
from enum import Enum
import logging
import statistics

from .features import (
    FeatureEngine,
    SymbolFeatures,
    TrendDirection,
    VolatilityRegime,
)
from .trading_intelligence import (
    TradingIntelligenceEngine,
    TradeScore,
    TradingSignal,
    VolatilityState,
    MomentumState,
    ReversalSignal,
    MarketPhase,
    TechnicalIndicators,
    VolatilitySurface,
    get_trading_intelligence,
)
from .strategy_matrix import (
    StrategyType,
    StrategyRecommendation,
    StrategySelectionEngine,
    get_strategy_engine,
)
from .candidates import (
    TradeCandidate,
    OptionLeg,
    CandidateStatus,
    CandidateGenerator,
    StrategyTemplate,
)
from .config import AutopilotConfig

logger = logging.getLogger(__name__)


# =============================================================================
# ENHANCED CANDIDATE DATA
# =============================================================================

@dataclass
class EnhancedCandidateMetadata:
    """Additional metadata for enhanced candidates."""
    # Intelligence Scores
    trade_score: TradeScore
    strategy_recommendation: StrategyRecommendation
    
    # Technical Analysis
    indicators: TechnicalIndicators
    vol_surface: VolatilitySurface
    
    # Market State
    momentum_state: MomentumState
    reversal_signal: ReversalSignal
    market_phase: MarketPhase
    vol_state: VolatilityState
    
    # Confidence & Reasoning
    overall_confidence: float
    bull_factors: List[str]
    bear_factors: List[str]
    entry_timing: str
    warnings: List[str]


# =============================================================================
# ENHANCED CANDIDATE GENERATOR
# =============================================================================

class EnhancedCandidateGenerator:
    """
    Enhanced candidate generator that uses the Trading Intelligence Engine
    and Strategy Selection Matrix for sophisticated trade selection.
    
    Key improvements:
    1. Multi-factor scoring (not just trend)
    2. Dynamic strategy selection based on IV regime
    3. Technical analysis integration (RSI, MACD, Bollinger)
    4. Mean reversion vs momentum detection
    5. Risk-adjusted position sizing
    6. Market phase awareness
    7. Volatility surface analysis
    """
    
    # Minimum scores to generate candidates
    MIN_TRADE_SCORE = 45
    MIN_STRATEGY_SCORE = 50
    MIN_CONFIDENCE = 0.35
    
    # DTE preferences by strategy
    STRATEGY_DTE_MAP = {
        StrategyType.PUT_CREDIT_SPREAD: (21, 45),
        StrategyType.CALL_CREDIT_SPREAD: (21, 45),
        StrategyType.IRON_CONDOR: (30, 60),
        StrategyType.CALL_DEBIT_SPREAD: (14, 30),
        StrategyType.PUT_DEBIT_SPREAD: (14, 30),
        StrategyType.LONG_CALL: (7, 21),
        StrategyType.LONG_PUT: (7, 21),
        StrategyType.IRON_BUTTERFLY: (21, 45),
        StrategyType.CALENDAR_SPREAD: (30, 60),
        StrategyType.LONG_STRADDLE: (21, 45),
    }
    
    def __init__(
        self,
        config: AutopilotConfig,
        base_generator: CandidateGenerator,
    ):
        self.config = config
        self.base_generator = base_generator
        self.intelligence = get_trading_intelligence()
        self.strategy_engine = get_strategy_engine()
        self._candidate_counter = 0
        
        # Price history cache for technical analysis
        self._price_history: Dict[str, List[float]] = {}
        self._volume_history: Dict[str, List[float]] = {}
        self._iv_history: Dict[str, List[float]] = {}
    
    def update_price_history(
        self,
        symbol: str,
        prices: List[float],
        volumes: Optional[List[float]] = None,
        ivs: Optional[List[float]] = None,
    ):
        """Update price history for a symbol (called during data refresh)."""
        self._price_history[symbol] = prices
        if volumes:
            self._volume_history[symbol] = volumes
        if ivs:
            self._iv_history[symbol] = ivs
    
    async def generate_enhanced_candidates(
        self,
        symbol: str,
        features: SymbolFeatures,
        option_chain: Dict[str, Any],
        weekly_only: bool = True,
    ) -> List[TradeCandidate]:
        """
        Generate enhanced candidates using multi-factor analysis.
        
        Args:
            symbol: Ticker symbol
            features: Pre-computed symbol features
            option_chain: Options chain data
            weekly_only: Whether to focus on weekly expiries
            
        Returns:
            List of high-quality trade candidates
        """
        # Get price history for technical analysis
        prices = self._price_history.get(symbol, [features.last_price] * 30)
        volumes = self._volume_history.get(symbol, [1_000_000] * 30)
        iv_history = self._iv_history.get(symbol)
        
        if len(prices) < 10:
            logger.debug(f"Insufficient price history for {symbol}, using basic generation")
            return await self.base_generator.generate(symbol, features, weekly_only)
        
        # Step 1: Compute comprehensive trade score
        trade_score = self.intelligence.score_trade_opportunity(
            symbol=symbol,
            prices=prices,
            volumes=volumes,
            atm_iv=features.realized_vol_20d,  # Approximation
            iv_history=iv_history,
        )
        
        logger.info(
            f"[{symbol}] Trade Score: {trade_score.composite_score:.1f} "
            f"({trade_score.direction.value}), Confidence: {trade_score.confidence:.2f}"
        )
        
        # Step 2: Check if trade score meets minimum
        if trade_score.composite_score < self.MIN_TRADE_SCORE:
            logger.debug(
                f"[{symbol}] Score {trade_score.composite_score:.1f} below minimum {self.MIN_TRADE_SCORE}"
            )
            return []
        
        if trade_score.confidence < self.MIN_CONFIDENCE:
            logger.debug(
                f"[{symbol}] Confidence {trade_score.confidence:.2f} below minimum {self.MIN_CONFIDENCE}"
            )
            return []
        
        # Step 3: Compute technical indicators
        indicators = self.intelligence.compute_technical_indicators(
            prices=prices,
            volumes=volumes,
        )
        
        # Step 4: Analyze volatility surface
        vol_surface = self.intelligence.analyze_volatility_surface(
            atm_iv=features.realized_vol_20d,
            put_ivs=[features.realized_vol_20d * 1.1],
            call_ivs=[features.realized_vol_20d * 0.95],
            front_iv=features.realized_vol_20d,
            back_iv=features.realized_vol_20d * 0.95,
            prices=prices,
            iv_history=iv_history,
        )
        vol_state = self.intelligence.get_volatility_state(vol_surface)
        
        # Step 5: Analyze momentum and mean reversion
        momentum_state, momentum_strength = self.intelligence.analyze_momentum(prices, indicators)
        reversal_signal, reversal_strength = self.intelligence.analyze_mean_reversion(prices, indicators)
        
        # Step 6: Detect market phase
        market_phase, phase_confidence = self.intelligence.detect_market_phase(
            prices, volumes, indicators
        )
        
        # Step 7: Get strategy recommendations
        strategy_recs = self.strategy_engine.select_strategies(
            trade_score=trade_score,
            iv_rank=features.iv_rank,
            momentum=momentum_state,
            market_phase=market_phase,
            vol_state=vol_state,
            reversal=reversal_signal,
            max_risk_per_trade=self.config.risk_limits.max_risk_per_trade,
            prefer_defined_risk=True,
            exclude_strategies=[StrategyType.NO_TRADE],
        )
        
        if not strategy_recs:
            logger.info(f"[{symbol}] No suitable strategies found")
            return []
        
        # Log top recommendations
        top_recs = strategy_recs[:3]
        for rec in top_recs:
            logger.info(
                f"[{symbol}] Strategy: {rec.strategy.value}, "
                f"Score: {rec.score:.1f}, Confidence: {rec.confidence:.2f}, "
                f"DTE: {rec.optimal_dte}, Delta: {rec.target_delta}"
            )
        
        # Step 8: Generate candidates for top strategies
        candidates = []
        for rec in top_recs:
            if rec.score < self.MIN_STRATEGY_SCORE:
                continue
            
            # Map StrategyType to StrategyTemplate
            template = self._map_strategy_to_template(rec.strategy)
            if not template:
                continue
            
            # Generate candidates for this strategy
            strategy_candidates = await self._generate_for_strategy(
                symbol=symbol,
                features=features,
                option_chain=option_chain,
                template=template,
                recommendation=rec,
                trade_score=trade_score,
                indicators=indicators,
                vol_surface=vol_surface,
                momentum_state=momentum_state,
                reversal_signal=reversal_signal,
                market_phase=market_phase,
                vol_state=vol_state,
            )
            
            candidates.extend(strategy_candidates)
        
        # Step 9: Score and rank candidates
        self._enhance_candidate_scores(
            candidates,
            trade_score,
            vol_state,
            momentum_state,
        )
        
        # Sort by adjusted score
        candidates.sort(key=lambda c: c.adjusted_score, reverse=True)
        
        logger.info(f"[{symbol}] Generated {len(candidates)} enhanced candidates")
        
        # Return top candidates
        return candidates[:5]
    
    async def _generate_for_strategy(
        self,
        symbol: str,
        features: SymbolFeatures,
        option_chain: Dict[str, Any],
        template: StrategyTemplate,
        recommendation: StrategyRecommendation,
        trade_score: TradeScore,
        indicators: TechnicalIndicators,
        vol_surface: VolatilitySurface,
        momentum_state: MomentumState,
        reversal_signal: ReversalSignal,
        market_phase: MarketPhase,
        vol_state: VolatilityState,
    ) -> List[TradeCandidate]:
        """Generate candidates for a specific strategy."""
        from .data_fetcher import get_data_provider
        
        provider = get_data_provider()
        price = features.last_price
        
        # Get optimal expiry based on recommendation
        target_dte = recommendation.optimal_dte
        expiry = self._find_optimal_expiry(option_chain, target_dte)
        if not expiry:
            return []
        
        actual_dte = (expiry - date.today()).days
        
        candidates = []
        
        # Generate based on template type
        if template == StrategyTemplate.PUT_CREDIT_SPREAD:
            candidates = self._generate_put_credit_spread(
                symbol, features, option_chain, price, expiry, actual_dte,
                recommendation.target_delta
            )
        
        elif template == StrategyTemplate.CALL_CREDIT_SPREAD:
            candidates = self._generate_call_credit_spread(
                symbol, features, option_chain, price, expiry, actual_dte,
                recommendation.target_delta
            )
        
        elif template == StrategyTemplate.IRON_CONDOR:
            candidates = self._generate_iron_condor(
                symbol, features, option_chain, price, expiry, actual_dte,
                recommendation.target_delta
            )
        
        elif template == StrategyTemplate.CALL_DEBIT_SPREAD:
            candidates = self._generate_call_debit_spread(
                symbol, features, option_chain, price, expiry, actual_dte,
                recommendation.target_delta
            )
        
        elif template == StrategyTemplate.PUT_DEBIT_SPREAD:
            candidates = self._generate_put_debit_spread(
                symbol, features, option_chain, price, expiry, actual_dte,
                recommendation.target_delta
            )
        
        # Enhance each candidate with metadata
        for cand in candidates:
            # Add selection reasoning
            cand.selection_reason = self._build_selection_reason(
                trade_score, recommendation, momentum_state, vol_state
            )
            
            # Store metadata in candidate (via custom field if needed)
            cand.metadata = {
                "intelligence_score": trade_score.composite_score,
                "strategy_score": recommendation.score,
                "confidence": recommendation.confidence,
                "momentum": momentum_state.value,
                "market_phase": market_phase.value,
                "vol_state": vol_state.value,
                "bull_factors": trade_score.bull_factors[:3],
                "bear_factors": trade_score.bear_factors[:3],
                "warnings": trade_score.warnings + recommendation.warnings,
            }
        
        return candidates
    
    def _map_strategy_to_template(self, strategy: StrategyType) -> Optional[StrategyTemplate]:
        """Map StrategyType to StrategyTemplate."""
        mapping = {
            StrategyType.PUT_CREDIT_SPREAD: StrategyTemplate.PUT_CREDIT_SPREAD,
            StrategyType.CALL_CREDIT_SPREAD: StrategyTemplate.CALL_CREDIT_SPREAD,
            StrategyType.IRON_CONDOR: StrategyTemplate.IRON_CONDOR,
            StrategyType.CALL_DEBIT_SPREAD: StrategyTemplate.CALL_DEBIT_SPREAD,
            StrategyType.PUT_DEBIT_SPREAD: StrategyTemplate.PUT_DEBIT_SPREAD,
            StrategyType.LONG_CALL: StrategyTemplate.LONG_CALL,
            StrategyType.LONG_PUT: StrategyTemplate.LONG_PUT,
        }
        return mapping.get(strategy)
    
    def _find_optimal_expiry(
        self,
        option_chain: Dict[str, Any],
        target_dte: int,
    ) -> Optional[date]:
        """Find the best expiry date near target DTE."""
        chains = option_chain.get("chains", {})
        if not chains:
            return None
        
        today = date.today()
        best_expiry = None
        best_distance = float('inf')
        
        for exp_str in chains.keys():
            try:
                exp_date = datetime.strptime(exp_str, "%Y-%m-%d").date()
                dte = (exp_date - today).days
                
                if dte < 1:  # Skip expired
                    continue
                
                distance = abs(dte - target_dte)
                if distance < best_distance:
                    best_distance = distance
                    best_expiry = exp_date
            except (ValueError, TypeError):
                continue
        
        return best_expiry
    
    def _generate_put_credit_spread(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
        target_delta: float,
    ) -> List[TradeCandidate]:
        """Generate put credit spread with dynamic delta targeting."""
        candidates = []
        
        exp_str = expiry.strftime("%Y-%m-%d")
        chains = chain.get("chains", {}).get(exp_str, {})
        puts = chains.get("puts", [])
        
        if len(puts) < 2:
            return candidates
        
        # Find OTM puts (below current price)
        otm_puts = [p for p in puts if p.get("strike", 0) < price]
        if len(otm_puts) < 2:
            return candidates
        
        # Find short put near target delta
        best_short = None
        best_delta_diff = float('inf')
        
        for put in otm_puts:
            delta = abs(put.get("delta", 0))
            diff = abs(delta - target_delta)
            if diff < best_delta_diff:
                best_delta_diff = diff
                best_short = put
        
        if not best_short:
            return candidates
        
        short_strike = best_short["strike"]
        short_delta = abs(best_short.get("delta", target_delta))
        
        # Try different spread widths
        for width in [2.5, 5, 10]:
            long_strike = short_strike - width
            
            # Find long put
            long_put = None
            for put in otm_puts:
                if abs(put["strike"] - long_strike) < 0.5:
                    long_put = put
                    break
            
            if not long_put:
                continue
            
            # Calculate credit
            credit = best_short.get("bid", 0) - long_put.get("ask", 0)
            if credit <= 0:
                continue
            
            max_loss = (width - credit) * 100
            max_profit = credit * 100
            
            if max_loss > self.config.risk_limits.max_risk_per_trade:
                continue
            
            if max_profit <= 0:
                continue
            
            # Calculate probability of profit
            pop = 1 - short_delta
            
            self._candidate_counter += 1
            candidate = TradeCandidate(
                id=f"enhanced-{symbol}-pcs-{self._candidate_counter}",
                symbol=symbol,
                template=StrategyTemplate.PUT_CREDIT_SPREAD,
                legs=[
                    OptionLeg(
                        option_type="put",
                        strike=short_strike,
                        expiry=expiry,
                        side="sell",
                        quantity=1,
                        premium=best_short.get("bid", 0),
                        delta=-short_delta,
                    ),
                    OptionLeg(
                        option_type="put",
                        strike=long_strike,
                        expiry=expiry,
                        side="buy",
                        quantity=1,
                        premium=long_put.get("ask", 0),
                        delta=-abs(long_put.get("delta", 0.10)),
                    ),
                ],
                underlying_price=price,
                max_loss=max_loss,
                max_profit=max_profit,
                pop=pop,
                dte=dte,
                iv_rank=features.iv_rank,
                liquidity_score=features.liquidity_score,
                spread_percent=features.avg_spread_pct,
                regime=features.vol_regime.value,
                trend=features.trend.value,
            )
            candidates.append(candidate)
            break  # One candidate per strategy
        
        return candidates
    
    def _generate_call_credit_spread(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
        target_delta: float,
    ) -> List[TradeCandidate]:
        """Generate call credit spread with dynamic delta targeting."""
        candidates = []
        
        exp_str = expiry.strftime("%Y-%m-%d")
        chains = chain.get("chains", {}).get(exp_str, {})
        calls = chains.get("calls", [])
        
        if len(calls) < 2:
            return candidates
        
        # Find OTM calls (above current price)
        otm_calls = [c for c in calls if c.get("strike", 0) > price]
        if len(otm_calls) < 2:
            return candidates
        
        # Find short call near target delta
        best_short = None
        best_delta_diff = float('inf')
        
        for call in otm_calls:
            delta = abs(call.get("delta", 0))
            diff = abs(delta - target_delta)
            if diff < best_delta_diff:
                best_delta_diff = diff
                best_short = call
        
        if not best_short:
            return candidates
        
        short_strike = best_short["strike"]
        short_delta = abs(best_short.get("delta", target_delta))
        
        for width in [2.5, 5, 10]:
            long_strike = short_strike + width
            
            long_call = None
            for call in otm_calls:
                if abs(call["strike"] - long_strike) < 0.5:
                    long_call = call
                    break
            
            if not long_call:
                continue
            
            credit = best_short.get("bid", 0) - long_call.get("ask", 0)
            if credit <= 0:
                continue
            
            max_loss = (width - credit) * 100
            max_profit = credit * 100
            
            if max_loss > self.config.risk_limits.max_risk_per_trade:
                continue
            
            pop = 1 - short_delta
            
            self._candidate_counter += 1
            candidate = TradeCandidate(
                id=f"enhanced-{symbol}-ccs-{self._candidate_counter}",
                symbol=symbol,
                template=StrategyTemplate.CALL_CREDIT_SPREAD,
                legs=[
                    OptionLeg(
                        option_type="call",
                        strike=short_strike,
                        expiry=expiry,
                        side="sell",
                        quantity=1,
                        premium=best_short.get("bid", 0),
                        delta=short_delta,
                    ),
                    OptionLeg(
                        option_type="call",
                        strike=long_strike,
                        expiry=expiry,
                        side="buy",
                        quantity=1,
                        premium=long_call.get("ask", 0),
                        delta=abs(long_call.get("delta", 0.10)),
                    ),
                ],
                underlying_price=price,
                max_loss=max_loss,
                max_profit=max_profit,
                pop=pop,
                dte=dte,
                iv_rank=features.iv_rank,
                liquidity_score=features.liquidity_score,
                spread_percent=features.avg_spread_pct,
                regime=features.vol_regime.value,
                trend=features.trend.value,
            )
            candidates.append(candidate)
            break
        
        return candidates
    
    def _generate_iron_condor(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
        target_delta: float,
    ) -> List[TradeCandidate]:
        """Generate iron condor for neutral plays."""
        candidates = []
        
        exp_str = expiry.strftime("%Y-%m-%d")
        chains = chain.get("chains", {}).get(exp_str, {})
        puts = chains.get("puts", [])
        calls = chains.get("calls", [])
        
        if len(puts) < 2 or len(calls) < 2:
            return candidates
        
        # Find OTM options
        otm_puts = [p for p in puts if p.get("strike", 0) < price]
        otm_calls = [c for c in calls if c.get("strike", 0) > price]
        
        if len(otm_puts) < 2 or len(otm_calls) < 2:
            return candidates
        
        # Find short put and short call near target delta
        short_put = min(otm_puts, key=lambda p: abs(abs(p.get("delta", 0)) - target_delta))
        short_call = min(otm_calls, key=lambda c: abs(abs(c.get("delta", 0)) - target_delta))
        
        for width in [2.5, 5]:
            long_put_strike = short_put["strike"] - width
            long_call_strike = short_call["strike"] + width
            
            # Find long options
            long_put = None
            long_call = None
            
            for p in otm_puts:
                if abs(p["strike"] - long_put_strike) < 0.5:
                    long_put = p
                    break
            
            for c in otm_calls:
                if abs(c["strike"] - long_call_strike) < 0.5:
                    long_call = c
                    break
            
            if not long_put or not long_call:
                continue
            
            # Calculate credits
            put_credit = short_put.get("bid", 0) - long_put.get("ask", 0)
            call_credit = short_call.get("bid", 0) - long_call.get("ask", 0)
            total_credit = put_credit + call_credit
            
            if total_credit <= 0:
                continue
            
            max_loss = (width - total_credit) * 100
            max_profit = total_credit * 100
            
            if max_loss > self.config.risk_limits.max_risk_per_trade:
                continue
            
            put_delta = abs(short_put.get("delta", target_delta))
            call_delta = abs(short_call.get("delta", target_delta))
            pop = (1 - put_delta) * (1 - call_delta)
            
            self._candidate_counter += 1
            candidate = TradeCandidate(
                id=f"enhanced-{symbol}-ic-{self._candidate_counter}",
                symbol=symbol,
                template=StrategyTemplate.IRON_CONDOR,
                legs=[
                    OptionLeg("put", short_put["strike"], expiry, "sell", 1,
                              short_put.get("bid", 0), -put_delta),
                    OptionLeg("put", long_put_strike, expiry, "buy", 1,
                              long_put.get("ask", 0)),
                    OptionLeg("call", short_call["strike"], expiry, "sell", 1,
                              short_call.get("bid", 0), call_delta),
                    OptionLeg("call", long_call_strike, expiry, "buy", 1,
                              long_call.get("ask", 0)),
                ],
                underlying_price=price,
                max_loss=max_loss,
                max_profit=max_profit,
                pop=pop,
                dte=dte,
                iv_rank=features.iv_rank,
                liquidity_score=features.liquidity_score,
                spread_percent=features.avg_spread_pct,
                regime=features.vol_regime.value,
                trend=features.trend.value,
            )
            candidates.append(candidate)
            break
        
        return candidates
    
    def _generate_call_debit_spread(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
        target_delta: float,
    ) -> List[TradeCandidate]:
        """Generate call debit spread for bullish directional plays."""
        candidates = []
        
        exp_str = expiry.strftime("%Y-%m-%d")
        chains = chain.get("chains", {}).get(exp_str, {})
        calls = chains.get("calls", [])
        
        if len(calls) < 2:
            return candidates
        
        # Find ATM/slightly OTM call to buy
        long_call = min(
            [c for c in calls if c.get("strike", 0) >= price * 0.97],
            key=lambda c: abs(abs(c.get("delta", 0)) - 0.50),
            default=None
        )
        
        if not long_call:
            return candidates
        
        long_strike = long_call["strike"]
        long_delta = abs(long_call.get("delta", 0.50))
        
        for width in [5, 10]:
            short_strike = long_strike + width
            
            short_call = None
            for c in calls:
                if abs(c["strike"] - short_strike) < 0.5:
                    short_call = c
                    break
            
            if not short_call:
                continue
            
            debit = long_call.get("ask", 0) - short_call.get("bid", 0)
            if debit <= 0:
                continue
            
            max_loss = debit * 100
            max_profit = (width - debit) * 100
            
            if max_loss > self.config.risk_limits.max_risk_per_trade:
                continue
            
            if max_profit <= 0:
                continue
            
            pop = long_delta * 0.6  # Discounted probability
            
            self._candidate_counter += 1
            candidate = TradeCandidate(
                id=f"enhanced-{symbol}-cds-{self._candidate_counter}",
                symbol=symbol,
                template=StrategyTemplate.CALL_DEBIT_SPREAD,
                legs=[
                    OptionLeg("call", long_strike, expiry, "buy", 1,
                              long_call.get("ask", 0), long_delta),
                    OptionLeg("call", short_strike, expiry, "sell", 1,
                              short_call.get("bid", 0)),
                ],
                underlying_price=price,
                max_loss=max_loss,
                max_profit=max_profit,
                pop=pop,
                dte=dte,
                iv_rank=features.iv_rank,
                liquidity_score=features.liquidity_score,
                spread_percent=features.avg_spread_pct,
                regime=features.vol_regime.value,
                trend=features.trend.value,
            )
            candidates.append(candidate)
            break
        
        return candidates
    
    def _generate_put_debit_spread(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
        target_delta: float,
    ) -> List[TradeCandidate]:
        """Generate put debit spread for bearish directional plays."""
        candidates = []
        
        exp_str = expiry.strftime("%Y-%m-%d")
        chains = chain.get("chains", {}).get(exp_str, {})
        puts = chains.get("puts", [])
        
        if len(puts) < 2:
            return candidates
        
        # Find ATM/slightly OTM put to buy
        long_put = min(
            [p for p in puts if p.get("strike", 0) <= price * 1.03],
            key=lambda p: abs(abs(p.get("delta", 0)) - 0.50),
            default=None
        )
        
        if not long_put:
            return candidates
        
        long_strike = long_put["strike"]
        long_delta = abs(long_put.get("delta", 0.50))
        
        for width in [5, 10]:
            short_strike = long_strike - width
            
            short_put = None
            for p in puts:
                if abs(p["strike"] - short_strike) < 0.5:
                    short_put = p
                    break
            
            if not short_put:
                continue
            
            debit = long_put.get("ask", 0) - short_put.get("bid", 0)
            if debit <= 0:
                continue
            
            max_loss = debit * 100
            max_profit = (width - debit) * 100
            
            if max_loss > self.config.risk_limits.max_risk_per_trade:
                continue
            
            if max_profit <= 0:
                continue
            
            pop = long_delta * 0.6
            
            self._candidate_counter += 1
            candidate = TradeCandidate(
                id=f"enhanced-{symbol}-pds-{self._candidate_counter}",
                symbol=symbol,
                template=StrategyTemplate.PUT_DEBIT_SPREAD,
                legs=[
                    OptionLeg("put", long_strike, expiry, "buy", 1,
                              long_put.get("ask", 0), -long_delta),
                    OptionLeg("put", short_strike, expiry, "sell", 1,
                              short_put.get("bid", 0)),
                ],
                underlying_price=price,
                max_loss=max_loss,
                max_profit=max_profit,
                pop=pop,
                dte=dte,
                iv_rank=features.iv_rank,
                liquidity_score=features.liquidity_score,
                spread_percent=features.avg_spread_pct,
                regime=features.vol_regime.value,
                trend=features.trend.value,
            )
            candidates.append(candidate)
            break
        
        return candidates
    
    def _enhance_candidate_scores(
        self,
        candidates: List[TradeCandidate],
        trade_score: TradeScore,
        vol_state: VolatilityState,
        momentum: MomentumState,
    ):
        """Apply enhanced scoring to candidates."""
        for cand in candidates:
            # Base score from features
            base = cand.liquidity_score * 30
            
            # Add intelligence score (0-100 scaled to 0-30)
            base += trade_score.composite_score * 0.3
            
            # Risk/reward bonus
            if cand.max_profit > 0 and cand.max_loss > 0:
                rr_ratio = cand.max_profit / cand.max_loss
                if rr_ratio > 0.5:
                    base += 10
                if rr_ratio > 1.0:
                    base += 10
            
            # POP bonus
            if cand.pop > 0.65:
                base += 15
            elif cand.pop > 0.55:
                base += 10
            
            # DTE penalty (too short or too long)
            if cand.dte < 7:
                base -= 10
            elif cand.dte > 60:
                base -= 5
            
            # IV rank bonus for credit strategies
            if cand.template in [StrategyTemplate.PUT_CREDIT_SPREAD, 
                                 StrategyTemplate.CALL_CREDIT_SPREAD,
                                 StrategyTemplate.IRON_CONDOR]:
                if cand.iv_rank > 60:
                    base += 10
                elif cand.iv_rank > 40:
                    base += 5
            
            # Vol state alignment
            if vol_state == VolatilityState.IV_RICH:
                if cand.template in [StrategyTemplate.PUT_CREDIT_SPREAD,
                                     StrategyTemplate.CALL_CREDIT_SPREAD,
                                     StrategyTemplate.IRON_CONDOR]:
                    base += 10
            
            # Momentum alignment
            if momentum in [MomentumState.STRONG_BULLISH, MomentumState.WEAK_BULLISH]:
                if cand.template == StrategyTemplate.PUT_CREDIT_SPREAD:
                    base += 5
                elif cand.template == StrategyTemplate.CALL_CREDIT_SPREAD:
                    base -= 5
            elif momentum in [MomentumState.STRONG_BEARISH, MomentumState.WEAK_BEARISH]:
                if cand.template == StrategyTemplate.CALL_CREDIT_SPREAD:
                    base += 5
                elif cand.template == StrategyTemplate.PUT_CREDIT_SPREAD:
                    base -= 5
            
            cand.base_score = base
            cand.adjusted_score = base * trade_score.confidence
    
    def _build_selection_reason(
        self,
        trade_score: TradeScore,
        recommendation: StrategyRecommendation,
        momentum: MomentumState,
        vol_state: VolatilityState,
    ) -> str:
        """Build human-readable selection reason."""
        reasons = []
        
        # Direction
        if trade_score.direction in [TradingSignal.STRONG_BUY, TradingSignal.BUY]:
            reasons.append("Bullish signal")
        elif trade_score.direction in [TradingSignal.STRONG_SELL, TradingSignal.SELL]:
            reasons.append("Bearish signal")
        else:
            reasons.append("Neutral signal")
        
        # Score
        reasons.append(f"Score: {trade_score.composite_score:.0f}")
        
        # Key factors
        if trade_score.bull_factors:
            reasons.append(trade_score.bull_factors[0])
        elif trade_score.bear_factors:
            reasons.append(trade_score.bear_factors[0])
        
        # Vol state
        if vol_state == VolatilityState.IV_RICH:
            reasons.append("IV rich")
        elif vol_state == VolatilityState.IV_CHEAP:
            reasons.append("IV cheap")
        
        # Momentum
        reasons.append(f"Momentum: {momentum.value}")
        
        return " | ".join(reasons)


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_enhanced_generator(
    config: AutopilotConfig,
    base_generator: CandidateGenerator,
) -> EnhancedCandidateGenerator:
    """Create an enhanced candidate generator."""
    return EnhancedCandidateGenerator(config, base_generator)
