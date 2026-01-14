"""
Candidate Generation Module
Generates deterministic trade candidates based on market conditions and strategy templates.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from enum import Enum
import logging

from .config import AutopilotConfig, StrategyTemplate
from .universe import UniverseManager, UniverseSymbol
from .features import FeatureEngine, SymbolFeatures, TrendDirection, VolatilityRegime

logger = logging.getLogger(__name__)


class CandidateStatus(Enum):
    """Status of a trade candidate"""
    PENDING = "pending"
    SELECTED = "selected"
    REJECTED = "rejected"
    EXECUTED = "executed"


@dataclass
class OptionLeg:
    """Single option leg in a strategy"""
    option_type: str  # "call" or "put"
    strike: float
    expiry: date
    side: str  # "buy" or "sell"
    quantity: int = 1
    premium: float = 0.0
    delta: float = 0.0
    gamma: float = 0.0
    theta: float = 0.0
    vega: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "option_type": self.option_type,
            "strike": self.strike,
            "expiry": self.expiry.isoformat() if self.expiry else None,
            "side": self.side,
            "quantity": self.quantity,
            "premium": self.premium,
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
        }


@dataclass
class TradeCandidate:
    """A potential trade candidate"""
    id: str
    symbol: str
    template: StrategyTemplate
    legs: List[OptionLeg]
    underlying_price: float
    max_loss: float  # Maximum risk
    max_profit: float  # Maximum potential profit
    pop: float  # Probability of profit (0-1)
    dte: int  # Days to expiration
    iv_rank: float
    liquidity_score: float
    spread_percent: float
    regime: str
    trend: str
    
    # Scoring
    base_score: float = 0.0
    adjusted_score: float = 0.0
    
    # Selection metadata
    status: CandidateStatus = CandidateStatus.PENDING
    selection_reason: str = ""
    rejection_reasons: List[str] = field(default_factory=list)
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def net_premium(self) -> float:
        """Calculate net premium (positive = credit, negative = debit)"""
        return sum(
            leg.premium * leg.quantity * (1 if leg.side == "sell" else -1)
            for leg in self.legs
        )
    
    def net_delta(self) -> float:
        """Calculate net delta exposure"""
        return sum(
            leg.delta * leg.quantity * (1 if leg.side == "buy" else -1)
            for leg in self.legs
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "template": self.template.value,
            "legs": [leg.to_dict() for leg in self.legs],
            "underlying_price": self.underlying_price,
            "max_loss": self.max_loss,
            "max_profit": self.max_profit,
            "pop": self.pop,
            "dte": self.dte,
            "iv_rank": self.iv_rank,
            "liquidity_score": self.liquidity_score,
            "spread_percent": self.spread_percent,
            "regime": self.regime,
            "trend": self.trend,
            "base_score": self.base_score,
            "adjusted_score": self.adjusted_score,
            "status": self.status.value,
            "selection_reason": self.selection_reason,
            "rejection_reasons": self.rejection_reasons,
            "net_premium": self.net_premium(),
            "net_delta": self.net_delta(),
            "created_at": self.created_at.isoformat(),
        }


class CandidateGenerator:
    """
    Generates trade candidates based on market conditions.
    Purely deterministic - no randomness or external LLM calls.
    """
    
    # DTE constraints per template
    DTE_CONSTRAINTS = {
        StrategyTemplate.PUT_CREDIT_SPREAD: (14, 45),
        StrategyTemplate.CALL_CREDIT_SPREAD: (14, 45),
        StrategyTemplate.IRON_CONDOR: (21, 45),
        StrategyTemplate.CALL_DEBIT_SPREAD: (14, 45),
        StrategyTemplate.PUT_DEBIT_SPREAD: (14, 45),
    }
    
    # Delta targets for short legs (credit spreads)
    CREDIT_DELTA_RANGE = (0.15, 0.35)
    
    # Spread width constraints (in dollars)
    SPREAD_WIDTH_RANGE = (1, 10)
    
    def __init__(
        self,
        config: AutopilotConfig,
        universe_manager: UniverseManager,
        feature_engine: FeatureEngine,
    ):
        self.config = config
        self.universe = universe_manager
        self.features = feature_engine
        self._candidate_counter = 0
    
    def generate_candidates(
        self,
        option_chains: Dict[str, Any],
        current_prices: Dict[str, float],
    ) -> List[TradeCandidate]:
        """
        Generate all valid trade candidates for the current market state.
        
        Args:
            option_chains: Options chain data keyed by symbol
            current_prices: Current underlying prices keyed by symbol
            
        Returns:
            List of TradeCandidate objects
        """
        candidates = []
        
        # Get tradeable symbols
        tradeable = self.universe.get_tradeable_symbols()
        
        for symbol_info in tradeable:
            symbol = symbol_info.symbol
            
            if symbol not in option_chains or symbol not in current_prices:
                logger.debug(f"Skipping {symbol}: missing data")
                continue
            
            # Compute features for this symbol
            features = self.features.compute_features(
                symbol=symbol,
                prices=current_prices.get(symbol, 0),
                option_chain=option_chains.get(symbol, {}),
            )
            
            if not features:
                logger.debug(f"Skipping {symbol}: could not compute features")
                continue
            
            # Generate candidates for each allowed template
            for template in self.config.strategy_constraints.allowed_templates:
                if self._is_template_eligible(template, features):
                    template_candidates = self._generate_for_template(
                        symbol=symbol,
                        template=template,
                        features=features,
                        chain=option_chains[symbol],
                        price=current_prices[symbol],
                    )
                    candidates.extend(template_candidates)
        
        # Score all candidates
        self._score_candidates(candidates)
        
        logger.info(f"Generated {len(candidates)} total candidates")
        return candidates
    
    def _is_template_eligible(
        self,
        template: StrategyTemplate,
        features: SymbolFeatures,
    ) -> bool:
        """Check if a template is eligible given current market features."""
        constraints = self.config.strategy_constraints
        
        # Check IV rank constraints
        if features.iv_rank < constraints.min_iv_rank:
            return False
        if features.iv_rank > constraints.max_iv_rank:
            return False
        
        # Check liquidity
        if features.liquidity_score < constraints.min_liquidity_score:
            return False
        
        # Template-specific regime checks
        if template in [StrategyTemplate.PUT_CREDIT_SPREAD, 
                        StrategyTemplate.CALL_CREDIT_SPREAD,
                        StrategyTemplate.IRON_CONDOR]:
            # Credit strategies prefer high IV and range-bound
            if features.iv_rank < 30:  # Need elevated IV for selling
                return False
            if features.volatility_regime == VolatilityRegime.LOW:
                return False
        
        elif template in [StrategyTemplate.CALL_DEBIT_SPREAD,
                          StrategyTemplate.PUT_DEBIT_SPREAD]:
            # Debit strategies prefer trending markets
            if features.trend_direction == TrendDirection.NEUTRAL:
                return False
            # Check directional alignment
            if template == StrategyTemplate.CALL_DEBIT_SPREAD:
                if features.trend_direction == TrendDirection.BEARISH:
                    return False
            elif template == StrategyTemplate.PUT_DEBIT_SPREAD:
                if features.trend_direction == TrendDirection.BULLISH:
                    return False
        
        return True
    
    def _generate_for_template(
        self,
        symbol: str,
        template: StrategyTemplate,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
    ) -> List[TradeCandidate]:
        """Generate candidates for a specific symbol and template."""
        candidates = []
        
        dte_min, dte_max = self.DTE_CONSTRAINTS.get(template, (14, 45))
        
        # Get available expiries in range
        expiries = self._get_expiries_in_range(chain, dte_min, dte_max)
        
        for expiry, dte in expiries[:3]:  # Limit to 3 expiries per template
            if template == StrategyTemplate.PUT_CREDIT_SPREAD:
                candidates.extend(
                    self._gen_put_credit_spread(symbol, features, chain, price, expiry, dte)
                )
            elif template == StrategyTemplate.CALL_CREDIT_SPREAD:
                candidates.extend(
                    self._gen_call_credit_spread(symbol, features, chain, price, expiry, dte)
                )
            elif template == StrategyTemplate.IRON_CONDOR:
                candidates.extend(
                    self._gen_iron_condor(symbol, features, chain, price, expiry, dte)
                )
            elif template == StrategyTemplate.CALL_DEBIT_SPREAD:
                candidates.extend(
                    self._gen_call_debit_spread(symbol, features, chain, price, expiry, dte)
                )
            elif template == StrategyTemplate.PUT_DEBIT_SPREAD:
                candidates.extend(
                    self._gen_put_debit_spread(symbol, features, chain, price, expiry, dte)
                )
        
        return candidates
    
    def _get_expiries_in_range(
        self,
        chain: Dict[str, Any],
        dte_min: int,
        dte_max: int,
    ) -> List[tuple]:
        """Get expiries within DTE range, returns list of (expiry_date, dte)."""
        expiries = []
        today = date.today()
        
        # Handle different chain formats
        if "expirations" in chain:
            for exp_str in chain["expirations"]:
                try:
                    exp_date = date.fromisoformat(exp_str)
                    dte = (exp_date - today).days
                    if dte_min <= dte <= dte_max:
                        expiries.append((exp_date, dte))
                except (ValueError, TypeError):
                    continue
        
        expiries.sort(key=lambda x: x[1])  # Sort by DTE
        return expiries
    
    def _gen_put_credit_spread(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
    ) -> List[TradeCandidate]:
        """Generate put credit spread candidates (bullish/neutral)."""
        candidates = []
        
        # Find strikes for short and long puts
        # Short put: target delta 0.15-0.35 OTM
        # Long put: 1-5 strikes below short
        
        puts = self._get_options_for_expiry(chain, expiry, "put")
        if len(puts) < 2:
            return candidates
        
        # Find short put strikes (OTM, below current price)
        otm_puts = [p for p in puts if p["strike"] < price]
        if len(otm_puts) < 2:
            return candidates
        
        # Select short leg based on delta target
        for short_put in otm_puts:
            delta = abs(short_put.get("delta", 0.20))
            if not (self.CREDIT_DELTA_RANGE[0] <= delta <= self.CREDIT_DELTA_RANGE[1]):
                continue
            
            short_strike = short_put["strike"]
            
            # Find long put strikes
            for width in [1, 2, 5]:
                long_strike = short_strike - width
                long_put = self._find_strike(puts, long_strike)
                
                if not long_put:
                    continue
                
                # Calculate P&L
                credit = short_put.get("bid", 0) - long_put.get("ask", 0)
                if credit <= 0:
                    continue
                
                max_loss = width - credit
                if max_loss <= 0:
                    continue
                
                max_profit = credit * 100  # Per contract
                max_loss_dollars = max_loss * 100
                
                # Check risk constraints
                if max_loss_dollars > self.config.risk_limits.max_risk_per_trade:
                    continue
                
                # Calculate POP (simplified: prob of staying above short strike)
                pop = 1 - delta  # Rough approximation
                
                candidate = self._create_candidate(
                    symbol=symbol,
                    template=StrategyTemplate.PUT_CREDIT_SPREAD,
                    features=features,
                    legs=[
                        OptionLeg(
                            option_type="put",
                            strike=short_strike,
                            expiry=expiry,
                            side="sell",
                            premium=short_put.get("bid", 0),
                            delta=-delta,
                        ),
                        OptionLeg(
                            option_type="put",
                            strike=long_strike,
                            expiry=expiry,
                            side="buy",
                            premium=long_put.get("ask", 0),
                            delta=-abs(long_put.get("delta", 0.10)),
                        ),
                    ],
                    underlying_price=price,
                    max_loss=max_loss_dollars,
                    max_profit=max_profit,
                    pop=pop,
                    dte=dte,
                )
                candidates.append(candidate)
                break  # One per short strike
        
        return candidates[:3]  # Limit per expiry
    
    def _gen_call_credit_spread(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
    ) -> List[TradeCandidate]:
        """Generate call credit spread candidates (bearish/neutral)."""
        candidates = []
        
        calls = self._get_options_for_expiry(chain, expiry, "call")
        if len(calls) < 2:
            return candidates
        
        # Find OTM calls (above current price)
        otm_calls = [c for c in calls if c["strike"] > price]
        if len(otm_calls) < 2:
            return candidates
        
        for short_call in otm_calls:
            delta = abs(short_call.get("delta", 0.20))
            if not (self.CREDIT_DELTA_RANGE[0] <= delta <= self.CREDIT_DELTA_RANGE[1]):
                continue
            
            short_strike = short_call["strike"]
            
            for width in [1, 2, 5]:
                long_strike = short_strike + width
                long_call = self._find_strike(calls, long_strike)
                
                if not long_call:
                    continue
                
                credit = short_call.get("bid", 0) - long_call.get("ask", 0)
                if credit <= 0:
                    continue
                
                max_loss = width - credit
                if max_loss <= 0:
                    continue
                
                max_profit = credit * 100
                max_loss_dollars = max_loss * 100
                
                if max_loss_dollars > self.config.risk_limits.max_risk_per_trade:
                    continue
                
                pop = 1 - delta
                
                candidate = self._create_candidate(
                    symbol=symbol,
                    template=StrategyTemplate.CALL_CREDIT_SPREAD,
                    features=features,
                    legs=[
                        OptionLeg(
                            option_type="call",
                            strike=short_strike,
                            expiry=expiry,
                            side="sell",
                            premium=short_call.get("bid", 0),
                            delta=delta,
                        ),
                        OptionLeg(
                            option_type="call",
                            strike=long_strike,
                            expiry=expiry,
                            side="buy",
                            premium=long_call.get("ask", 0),
                            delta=abs(long_call.get("delta", 0.10)),
                        ),
                    ],
                    underlying_price=price,
                    max_loss=max_loss_dollars,
                    max_profit=max_profit,
                    pop=pop,
                    dte=dte,
                )
                candidates.append(candidate)
                break
        
        return candidates[:3]
    
    def _gen_iron_condor(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
    ) -> List[TradeCandidate]:
        """Generate iron condor candidates (neutral/range-bound)."""
        candidates = []
        
        puts = self._get_options_for_expiry(chain, expiry, "put")
        calls = self._get_options_for_expiry(chain, expiry, "call")
        
        if len(puts) < 2 or len(calls) < 2:
            return candidates
        
        # Find OTM options
        otm_puts = [p for p in puts if p["strike"] < price]
        otm_calls = [c for c in calls if c["strike"] > price]
        
        if len(otm_puts) < 2 or len(otm_calls) < 2:
            return candidates
        
        # Find short put (15-25 delta)
        for short_put in otm_puts:
            put_delta = abs(short_put.get("delta", 0.20))
            if not (0.15 <= put_delta <= 0.25):
                continue
            
            # Find short call with similar delta
            for short_call in otm_calls:
                call_delta = abs(short_call.get("delta", 0.20))
                if not (0.15 <= call_delta <= 0.25):
                    continue
                
                short_put_strike = short_put["strike"]
                short_call_strike = short_call["strike"]
                
                # Use same width on both sides
                for width in [2, 5]:
                    long_put_strike = short_put_strike - width
                    long_call_strike = short_call_strike + width
                    
                    long_put = self._find_strike(puts, long_put_strike)
                    long_call = self._find_strike(calls, long_call_strike)
                    
                    if not long_put or not long_call:
                        continue
                    
                    # Calculate total credit
                    put_credit = short_put.get("bid", 0) - long_put.get("ask", 0)
                    call_credit = short_call.get("bid", 0) - long_call.get("ask", 0)
                    total_credit = put_credit + call_credit
                    
                    if total_credit <= 0:
                        continue
                    
                    max_loss = width - total_credit
                    if max_loss <= 0:
                        continue
                    
                    max_profit = total_credit * 100
                    max_loss_dollars = max_loss * 100
                    
                    if max_loss_dollars > self.config.risk_limits.max_risk_per_trade:
                        continue
                    
                    # POP for IC: prob of staying between short strikes
                    pop = (1 - put_delta) * (1 - call_delta)
                    
                    candidate = self._create_candidate(
                        symbol=symbol,
                        template=StrategyTemplate.IRON_CONDOR,
                        features=features,
                        legs=[
                            OptionLeg("put", short_put_strike, expiry, "sell", 
                                      premium=short_put.get("bid", 0), delta=-put_delta),
                            OptionLeg("put", long_put_strike, expiry, "buy",
                                      premium=long_put.get("ask", 0)),
                            OptionLeg("call", short_call_strike, expiry, "sell",
                                      premium=short_call.get("bid", 0), delta=call_delta),
                            OptionLeg("call", long_call_strike, expiry, "buy",
                                      premium=long_call.get("ask", 0)),
                        ],
                        underlying_price=price,
                        max_loss=max_loss_dollars,
                        max_profit=max_profit,
                        pop=pop,
                        dte=dte,
                    )
                    candidates.append(candidate)
                    break
                break
        
        return candidates[:2]
    
    def _gen_call_debit_spread(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
    ) -> List[TradeCandidate]:
        """Generate call debit spread candidates (bullish directional)."""
        candidates = []
        
        calls = self._get_options_for_expiry(chain, expiry, "call")
        if len(calls) < 2:
            return candidates
        
        # Buy ATM/slightly OTM, sell further OTM
        for long_call in calls:
            long_strike = long_call["strike"]
            # Target slightly OTM (within 3% of price)
            if not (price * 0.97 <= long_strike <= price * 1.03):
                continue
            
            long_delta = abs(long_call.get("delta", 0.50))
            if long_delta < 0.40:  # Need reasonable delta
                continue
            
            for width in [2, 5, 10]:
                short_strike = long_strike + width
                short_call = self._find_strike(calls, short_strike)
                
                if not short_call:
                    continue
                
                debit = long_call.get("ask", 0) - short_call.get("bid", 0)
                if debit <= 0:
                    continue
                
                max_profit = (width - debit) * 100
                max_loss_dollars = debit * 100
                
                if max_loss_dollars > self.config.risk_limits.max_risk_per_trade:
                    continue
                
                if max_profit <= 0:
                    continue
                
                # POP for debit spread (rough: based on long delta)
                pop = long_delta * 0.6  # Discounted
                
                candidate = self._create_candidate(
                    symbol=symbol,
                    template=StrategyTemplate.CALL_DEBIT_SPREAD,
                    features=features,
                    legs=[
                        OptionLeg("call", long_strike, expiry, "buy",
                                  premium=long_call.get("ask", 0), delta=long_delta),
                        OptionLeg("call", short_strike, expiry, "sell",
                                  premium=short_call.get("bid", 0)),
                    ],
                    underlying_price=price,
                    max_loss=max_loss_dollars,
                    max_profit=max_profit,
                    pop=pop,
                    dte=dte,
                )
                candidates.append(candidate)
                break
        
        return candidates[:3]
    
    def _gen_put_debit_spread(
        self,
        symbol: str,
        features: SymbolFeatures,
        chain: Dict[str, Any],
        price: float,
        expiry: date,
        dte: int,
    ) -> List[TradeCandidate]:
        """Generate put debit spread candidates (bearish directional)."""
        candidates = []
        
        puts = self._get_options_for_expiry(chain, expiry, "put")
        if len(puts) < 2:
            return candidates
        
        # Buy ATM/slightly OTM put, sell further OTM
        for long_put in puts:
            long_strike = long_put["strike"]
            # Target slightly OTM (within 3% of price)
            if not (price * 0.97 <= long_strike <= price * 1.03):
                continue
            
            long_delta = abs(long_put.get("delta", 0.50))
            if long_delta < 0.40:
                continue
            
            for width in [2, 5, 10]:
                short_strike = long_strike - width
                short_put = self._find_strike(puts, short_strike)
                
                if not short_put:
                    continue
                
                debit = long_put.get("ask", 0) - short_put.get("bid", 0)
                if debit <= 0:
                    continue
                
                max_profit = (width - debit) * 100
                max_loss_dollars = debit * 100
                
                if max_loss_dollars > self.config.risk_limits.max_risk_per_trade:
                    continue
                
                if max_profit <= 0:
                    continue
                
                pop = long_delta * 0.6
                
                candidate = self._create_candidate(
                    symbol=symbol,
                    template=StrategyTemplate.PUT_DEBIT_SPREAD,
                    features=features,
                    legs=[
                        OptionLeg("put", long_strike, expiry, "buy",
                                  premium=long_put.get("ask", 0), delta=-long_delta),
                        OptionLeg("put", short_strike, expiry, "sell",
                                  premium=short_put.get("bid", 0)),
                    ],
                    underlying_price=price,
                    max_loss=max_loss_dollars,
                    max_profit=max_profit,
                    pop=pop,
                    dte=dte,
                )
                candidates.append(candidate)
                break
        
        return candidates[:3]
    
    def _get_options_for_expiry(
        self,
        chain: Dict[str, Any],
        expiry: date,
        option_type: str,
    ) -> List[Dict[str, Any]]:
        """Get options for a specific expiry and type."""
        options = []
        expiry_str = expiry.isoformat()
        
        # Handle different chain formats
        if "chains" in chain:
            expiry_chain = chain["chains"].get(expiry_str, {})
            options = expiry_chain.get(f"{option_type}s", [])
        elif "options" in chain:
            for opt in chain["options"]:
                if (opt.get("expiry") == expiry_str and 
                    opt.get("type") == option_type):
                    options.append(opt)
        
        return sorted(options, key=lambda x: x.get("strike", 0))
    
    def _find_strike(
        self,
        options: List[Dict[str, Any]],
        target_strike: float,
    ) -> Optional[Dict[str, Any]]:
        """Find option with exact strike."""
        for opt in options:
            if abs(opt.get("strike", 0) - target_strike) < 0.01:
                return opt
        return None
    
    def _create_candidate(
        self,
        symbol: str,
        template: StrategyTemplate,
        features: SymbolFeatures,
        legs: List[OptionLeg],
        underlying_price: float,
        max_loss: float,
        max_profit: float,
        pop: float,
        dte: int,
    ) -> TradeCandidate:
        """Create a candidate with all metadata."""
        self._candidate_counter += 1
        
        return TradeCandidate(
            id=f"C{self._candidate_counter:06d}",
            symbol=symbol,
            template=template,
            legs=legs,
            underlying_price=underlying_price,
            max_loss=max_loss,
            max_profit=max_profit,
            pop=pop,
            dte=dte,
            iv_rank=features.iv_rank,
            liquidity_score=features.liquidity_score,
            spread_percent=features.avg_spread_percent,
            regime=features.volatility_regime.value,
            trend=features.trend_direction.value,
        )
    
    def _score_candidates(self, candidates: List[TradeCandidate]) -> None:
        """Score all candidates for ranking."""
        for candidate in candidates:
            # Base score components
            risk_reward = candidate.max_profit / max(candidate.max_loss, 1)
            pop_score = candidate.pop * 100
            iv_score = candidate.iv_rank if candidate.template in [
                StrategyTemplate.PUT_CREDIT_SPREAD,
                StrategyTemplate.CALL_CREDIT_SPREAD,
                StrategyTemplate.IRON_CONDOR,
            ] else 100 - candidate.iv_rank
            liquidity_score = candidate.liquidity_score
            
            # Weighted base score
            candidate.base_score = (
                risk_reward * 20 +
                pop_score * 0.3 +
                iv_score * 0.2 +
                liquidity_score * 0.3
            )
            
            # Adjusted score starts as base score
            candidate.adjusted_score = candidate.base_score
