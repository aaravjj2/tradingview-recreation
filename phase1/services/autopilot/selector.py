"""
Selector Module
Implements candidate ranking and selection strategies.
Supports both deterministic and LLM-based selection.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime
import logging

from .candidates import TradeCandidate, CandidateStatus
from .config import AutopilotConfig

logger = logging.getLogger(__name__)


@dataclass
class SelectionResult:
    """Result of a selection process"""
    selected: List[TradeCandidate]
    rejected: List[TradeCandidate]
    method: str  # "deterministic" or "llm"
    rationale: str
    timestamp: datetime
    llm_available: bool = True
    fallback_used: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_count": len(self.selected),
            "rejected_count": len(self.rejected),
            "selected_ids": [c.id for c in self.selected],
            "method": self.method,
            "rationale": self.rationale,
            "timestamp": self.timestamp.isoformat(),
            "llm_available": self.llm_available,
            "fallback_used": self.fallback_used,
        }


class CandidateSelector(ABC):
    """Abstract base class for candidate selection strategies"""
    
    @abstractmethod
    def select(
        self,
        candidates: List[TradeCandidate],
        config: AutopilotConfig,
        portfolio_state: Dict[str, Any],
        market_context: Dict[str, Any],
    ) -> SelectionResult:
        """
        Select candidates from the available pool.
        
        Args:
            candidates: All generated candidates
            config: Autopilot configuration
            portfolio_state: Current portfolio positions and risk metrics
            market_context: Market regime and other context
            
        Returns:
            SelectionResult with selected and rejected candidates
        """
        pass


class DeterministicRanker(CandidateSelector):
    """
    Pure deterministic candidate selection based on scoring rules.
    This is the default and test-friendly selector.
    """
    
    def __init__(self):
        self.name = "deterministic"
    
    def select(
        self,
        candidates: List[TradeCandidate],
        config: AutopilotConfig,
        portfolio_state: Dict[str, Any],
        market_context: Dict[str, Any],
    ) -> SelectionResult:
        """
        Select candidates using deterministic scoring.
        
        Selection rules:
        1. Apply forecast adjustments to scores
        2. Apply concentration filters
        3. Sort by adjusted score
        4. Select top N within risk budget
        """
        if not candidates:
            return SelectionResult(
                selected=[],
                rejected=[],
                method=self.name,
                rationale="No candidates available",
                timestamp=datetime.utcnow(),
            )
        
        # Apply forecast influence to scores
        self._apply_forecast_influence(candidates, market_context, config)
        
        # Get current exposure info
        current_risk = portfolio_state.get("total_risk", 0)
        current_positions = portfolio_state.get("position_count", 0)
        symbol_exposure = portfolio_state.get("symbol_exposure", {})
        cluster_exposure = portfolio_state.get("cluster_exposure", {})
        
        # Available budget
        risk_budget = config.risk_limits.max_total_risk - current_risk
        position_budget = config.risk_limits.max_open_positions - current_positions
        
        if risk_budget <= 0 or position_budget <= 0:
            for c in candidates:
                c.status = CandidateStatus.REJECTED
                c.rejection_reasons.append("Risk/position budget exhausted")
            return SelectionResult(
                selected=[],
                rejected=candidates,
                method=self.name,
                rationale="Risk or position budget exhausted",
                timestamp=datetime.utcnow(),
            )
        
        # Sort by adjusted score (descending)
        sorted_candidates = sorted(
            candidates, 
            key=lambda c: c.adjusted_score, 
            reverse=True
        )
        
        selected = []
        rejected = []
        remaining_risk = risk_budget
        remaining_positions = position_budget
        
        # Track selections per symbol and cluster for concentration
        selected_per_symbol: Dict[str, int] = {}
        selected_per_cluster: Dict[str, float] = {}
        
        for candidate in sorted_candidates:
            # Check if we can add this trade
            if remaining_positions <= 0:
                candidate.status = CandidateStatus.REJECTED
                candidate.rejection_reasons.append("Position limit reached")
                rejected.append(candidate)
                continue
            
            if candidate.max_loss > remaining_risk:
                candidate.status = CandidateStatus.REJECTED
                candidate.rejection_reasons.append(
                    f"Insufficient risk budget: {candidate.max_loss:.0f} > {remaining_risk:.0f}"
                )
                rejected.append(candidate)
                continue
            
            # Check symbol concentration
            symbol_count = (
                symbol_exposure.get(candidate.symbol, 0) + 
                selected_per_symbol.get(candidate.symbol, 0)
            )
            if symbol_count >= config.risk_limits.max_positions_per_underlying:
                candidate.status = CandidateStatus.REJECTED
                candidate.rejection_reasons.append(
                    f"Symbol concentration limit: {candidate.symbol}"
                )
                rejected.append(candidate)
                continue
            
            # Check cluster concentration
            cluster = self._get_cluster(candidate.symbol)
            cluster_risk = (
                cluster_exposure.get(cluster, 0) + 
                selected_per_cluster.get(cluster, 0) +
                candidate.max_loss
            )
            max_cluster_risk = config.risk_limits.max_total_risk * 0.6  # 60% cap
            if cluster_risk > max_cluster_risk:
                candidate.status = CandidateStatus.REJECTED
                candidate.rejection_reasons.append(
                    f"Cluster concentration limit: {cluster}"
                )
                rejected.append(candidate)
                continue
            
            # Select this candidate
            candidate.status = CandidateStatus.SELECTED
            candidate.selection_reason = (
                f"Score: {candidate.adjusted_score:.1f}, "
                f"R/R: {candidate.max_profit/candidate.max_loss:.2f}, "
                f"POP: {candidate.pop:.0%}"
            )
            selected.append(candidate)
            
            # Update tracking
            remaining_risk -= candidate.max_loss
            remaining_positions -= 1
            selected_per_symbol[candidate.symbol] = selected_per_symbol.get(candidate.symbol, 0) + 1
            selected_per_cluster[cluster] = selected_per_cluster.get(cluster, 0) + candidate.max_loss
        
        # Generate rationale
        rationale = self._generate_rationale(selected, rejected, config)
        
        return SelectionResult(
            selected=selected,
            rejected=rejected,
            method=self.name,
            rationale=rationale,
            timestamp=datetime.utcnow(),
        )
    
    def _apply_forecast_influence(
        self,
        candidates: List[TradeCandidate],
        market_context: Dict[str, Any],
        config: AutopilotConfig,
    ) -> None:
        """Apply forecast data to adjust candidate scores."""
        forecasts = market_context.get("forecasts", {})
        influence_level = config.forecast_settings.influence_level
        
        if influence_level == 0 or not forecasts:
            return
        
        for candidate in candidates:
            forecast = forecasts.get(candidate.symbol)
            if not forecast:
                continue
            
            # Get forecast direction
            p50_5d = forecast.get("p50_5d", 0)
            confidence = forecast.get("confidence", 0.5)
            
            # Scale influence by confidence
            effective_influence = influence_level * confidence
            
            # Apply directional adjustment
            if candidate.template.value in ["put_credit_spread", "call_debit_spread"]:
                # Bullish strategies
                if p50_5d > 0:
                    candidate.adjusted_score *= (1 + 0.1 * effective_influence)
                elif p50_5d < 0:
                    candidate.adjusted_score *= (1 - 0.1 * effective_influence)
            
            elif candidate.template.value in ["call_credit_spread", "put_debit_spread"]:
                # Bearish strategies
                if p50_5d < 0:
                    candidate.adjusted_score *= (1 + 0.1 * effective_influence)
                elif p50_5d > 0:
                    candidate.adjusted_score *= (1 - 0.1 * effective_influence)
            
            # Iron condor: penalize if expecting big move
            elif candidate.template.value == "iron_condor":
                if abs(p50_5d) > 0.03:  # >3% expected move
                    candidate.adjusted_score *= (1 - 0.15 * effective_influence)
    
    def _get_cluster(self, symbol: str) -> str:
        """Map symbol to cluster for concentration tracking."""
        CLUSTERS = {
            "tech": ["AAPL", "MSFT", "NVDA", "GOOGL", "META", "AMZN", "AMD", "QQQ", "XLK", "SMH"],
            "broad": ["SPY", "IWM", "DIA"],
            "financials": ["XLF"],
            "energy": ["XLE"],
            "bonds": ["TLT"],
            "commodities": ["GLD"],
        }
        
        for cluster, symbols in CLUSTERS.items():
            if symbol in symbols:
                return cluster
        return "other"
    
    def _generate_rationale(
        self,
        selected: List[TradeCandidate],
        rejected: List[TradeCandidate],
        config: AutopilotConfig,
    ) -> str:
        """Generate human-readable selection rationale."""
        if not selected:
            reasons = set()
            for c in rejected[:5]:
                reasons.update(c.rejection_reasons)
            return f"No trades selected. Top rejection reasons: {', '.join(reasons)}"
        
        templates = {}
        for c in selected:
            t = c.template.value
            templates[t] = templates.get(t, 0) + 1
        
        template_summary = ", ".join(f"{k}: {v}" for k, v in templates.items())
        total_risk = sum(c.max_loss for c in selected)
        
        return (
            f"Selected {len(selected)} trades ({template_summary}). "
            f"Total risk: ${total_risk:.0f}. "
            f"Avg score: {sum(c.adjusted_score for c in selected)/len(selected):.1f}"
        )


class LLMRanker(CandidateSelector):
    """
    LLM-assisted candidate selection.
    Falls back to deterministic if LLM unavailable.
    """
    
    def __init__(self, llm_provider=None):
        self.name = "llm"
        self.llm_provider = llm_provider
        self.deterministic_fallback = DeterministicRanker()
    
    def select(
        self,
        candidates: List[TradeCandidate],
        config: AutopilotConfig,
        portfolio_state: Dict[str, Any],
        market_context: Dict[str, Any],
    ) -> SelectionResult:
        """
        Select candidates using LLM ranking.
        Falls back to deterministic if LLM unavailable.
        """
        if not self.llm_provider or not config.llm_settings.enabled:
            logger.info("LLM disabled or unavailable, using deterministic fallback")
            result = self.deterministic_fallback.select(
                candidates, config, portfolio_state, market_context
            )
            result.method = f"{self.name} (fallback: deterministic)"
            result.llm_available = False
            result.fallback_used = True
            return result
        
        try:
            # Prepare context for LLM
            llm_context = self._prepare_llm_context(
                candidates, config, portfolio_state, market_context
            )
            
            # Call LLM for ranking
            llm_response = self.llm_provider.rank_candidates(llm_context)
            
            if not llm_response or "error" in llm_response:
                raise ValueError(f"LLM error: {llm_response.get('error', 'Unknown')}")
            
            # Apply LLM selections
            return self._apply_llm_selections(
                candidates, llm_response, config, portfolio_state
            )
            
        except Exception as e:
            logger.warning(f"LLM selection failed: {e}, using fallback")
            result = self.deterministic_fallback.select(
                candidates, config, portfolio_state, market_context
            )
            result.method = f"{self.name} (fallback: deterministic)"
            result.llm_available = False
            result.fallback_used = True
            result.rationale = f"LLM failed ({str(e)[:50]}), {result.rationale}"
            return result
    
    def _prepare_llm_context(
        self,
        candidates: List[TradeCandidate],
        config: AutopilotConfig,
        portfolio_state: Dict[str, Any],
        market_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Prepare structured context for LLM."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "market_regime": market_context.get("regime", "unknown"),
            "vix_level": market_context.get("vix", 20),
            "portfolio": {
                "equity": config.paper_equity,
                "current_risk": portfolio_state.get("total_risk", 0),
                "position_count": portfolio_state.get("position_count", 0),
                "max_risk_per_trade": config.risk_limits.max_risk_per_trade,
                "max_total_risk": config.risk_limits.max_total_risk,
            },
            "candidates": [
                {
                    "id": c.id,
                    "symbol": c.symbol,
                    "template": c.template.value,
                    "max_loss": c.max_loss,
                    "max_profit": c.max_profit,
                    "pop": c.pop,
                    "dte": c.dte,
                    "iv_rank": c.iv_rank,
                    "liquidity_score": c.liquidity_score,
                    "trend": c.trend,
                    "regime": c.regime,
                    "base_score": c.base_score,
                }
                for c in candidates[:20]  # Limit to top 20
            ],
            "instructions": (
                "Select up to 5 candidates that best fit the portfolio goals. "
                "Prioritize: high POP, good R/R, high liquidity. "
                "Avoid over-concentration in any single symbol or sector. "
                "Return a JSON object with 'selected_ids' array and 'explanation' string."
            ),
        }
    
    def _apply_llm_selections(
        self,
        candidates: List[TradeCandidate],
        llm_response: Dict[str, Any],
        config: AutopilotConfig,
        portfolio_state: Dict[str, Any],
    ) -> SelectionResult:
        """Apply LLM selections to candidates."""
        selected_ids = set(llm_response.get("selected_ids", []))
        explanation = llm_response.get("explanation", "LLM selection")
        
        selected = []
        rejected = []
        
        # Respect risk limits even for LLM selections
        remaining_risk = config.risk_limits.max_total_risk - portfolio_state.get("total_risk", 0)
        remaining_positions = config.risk_limits.max_open_positions - portfolio_state.get("position_count", 0)
        
        for candidate in candidates:
            if candidate.id in selected_ids:
                if remaining_positions > 0 and candidate.max_loss <= remaining_risk:
                    candidate.status = CandidateStatus.SELECTED
                    candidate.selection_reason = "LLM selected"
                    selected.append(candidate)
                    remaining_risk -= candidate.max_loss
                    remaining_positions -= 1
                else:
                    candidate.status = CandidateStatus.REJECTED
                    candidate.rejection_reasons.append("LLM selected but exceeded limits")
                    rejected.append(candidate)
            else:
                candidate.status = CandidateStatus.REJECTED
                candidate.rejection_reasons.append("Not selected by LLM")
                rejected.append(candidate)
        
        return SelectionResult(
            selected=selected,
            rejected=rejected,
            method=self.name,
            rationale=explanation,
            timestamp=datetime.utcnow(),
            llm_available=True,
            fallback_used=False,
        )


def create_selector(config: AutopilotConfig, llm_provider=None) -> CandidateSelector:
    """
    Factory function to create appropriate selector based on config.
    
    Supports:
    - Deterministic (default)
    - Groq (fast ranking)
    - Gemini (detailed validation)
    - Hybrid (Groq → Gemini)
    """
    from .config import LLMMode
    
    # Check if LLM enabled and mode specified
    if not config.llm_settings.enabled or config.llm_settings.mode == LLMMode.OFF:
        logger.info("LLM disabled, using deterministic ranker")
        return DeterministicRanker()
    
    if config.llm_settings.mode == LLMMode.DETERMINISTIC:
        logger.info("LLM mode set to deterministic")
        return DeterministicRanker()
    
    # Hybrid mode: use both Groq and Gemini
    if config.llm_settings.mode == LLMMode.HYBRID:
        try:
            from .hybrid_selector import create_hybrid_selector
            selector = create_hybrid_selector()
            logger.info("Using hybrid Groq+Gemini selector")
            return selector
        except Exception as e:
            logger.warning(f"Failed to create hybrid selector: {e}, falling back to deterministic")
            return DeterministicRanker()
    
    # Single LLM mode: Groq or Gemini
    if llm_provider:
        return LLMRanker(llm_provider)
    
    # Try to create the specified provider
    if config.llm_settings.mode == LLMMode.GROQ:
        try:
            from ..llm.providers import create_groq_provider
            provider = create_groq_provider(model=config.llm_settings.groq_model)
            if provider.is_available:
                logger.info("Using Groq provider for LLM ranking")
                return LLMRanker(provider)
            else:
                logger.warning("Groq provider not available (missing API key)")
        except Exception as e:
            logger.warning(f"Failed to create Groq provider: {e}")
    
    elif config.llm_settings.mode == LLMMode.GEMINI:
        try:
            from ..llm.providers import create_gemini_provider
            provider = create_gemini_provider(model=config.llm_settings.gemini_model)
            if provider.is_available:
                logger.info("Using Gemini provider for LLM ranking")
                return LLMRanker(provider)
            else:
                logger.warning("Gemini provider not available (missing API key)")
        except Exception as e:
            logger.warning(f"Failed to create Gemini provider: {e}")
    
    # Fallback to deterministic
    logger.warning("No LLM providers available, falling back to deterministic ranker")
    return DeterministicRanker()

