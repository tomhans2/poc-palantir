"""Private Banking domain action functions — L2/L3 intelligence for HNW client management.

Custom functions automatically loaded when the 'private_banking' sample is selected.
These functions augment the built-in generic functions (set_property, adjust_numeric, etc.)
with domain-specific private banking intelligence.

All functions follow the uniform signature: (ctx: ActionContext) -> ActionResult
"""

from app.engine.action_registry import ActionContext, ActionResult, register_action


# ---------------------------------------------------------------------------
# L2 Information Layer — Private Banking Business Logic
# ---------------------------------------------------------------------------

@register_action
def pb_assess_aum_impact(ctx: ActionContext) -> ActionResult:
    """Assess AUM impact from a major client life event.

    Computes the new AUM based on the event type and uplift factor,
    reflecting how major life events (IPO, divorce, etc.) affect
    the client's managed asset scale.

    Params:
        event_type (str): Type of event (IPO_SUCCESS, DIVORCE, etc.)
        uplift_factor (float): AUM change factor (positive = growth, negative = decline)
    """
    event_type = ctx.params.get("event_type", "UNKNOWN")
    uplift_factor = ctx.params.get("uplift_factor", 0)
    old_aum = ctx.target_node.get("aum", 0)
    new_aum = old_aum * (1 + uplift_factor)

    return ActionResult(
        updated_properties={
            "aum": new_aum,
            "last_aum_event": event_type,
        },
        old_values={"aum": old_aum},
    )


@register_action
def pb_compute_reinvestment(ctx: ActionContext) -> ActionResult:
    """Compute reinvestment need when financial products mature.

    Calculates the amount of capital that needs to be reallocated based
    on the client's total AUM and the reinvestment ratio. This helps
    private bankers proactively prepare alternative investment proposals.

    Params:
        amount_property (str): Property name for the base amount (default 'aum')
        reinvest_ratio (float): Ratio of base amount needing reinvestment
    """
    amount_property = ctx.params.get("amount_property", "aum")
    reinvest_ratio = ctx.params.get("reinvest_ratio", 0.1)
    current_amount = ctx.target_node.get(amount_property, 0)
    reinvest_amount = current_amount * reinvest_ratio

    return ActionResult(
        updated_properties={
            "reinvestment_need": reinvest_amount,
            "reinvestment_status": "PENDING",
        },
        old_values={amount_property: current_amount},
    )


@register_action
def pb_assess_offshore_demand(ctx: ActionContext) -> ActionResult:
    """Assess offshore financial demand triggered by family events.

    Evaluates the cross-border financial service needs when events like
    children studying abroad create demand for foreign currency, overseas
    real estate, and international insurance products.

    Params:
        annual_cost (float): Estimated annual overseas expenditure (in CNY)
    """
    annual_cost = ctx.params.get("annual_cost", 0)
    old_aum = ctx.target_node.get("aum", 0)
    # Five-year planning horizon for education expenses
    five_year_total = annual_cost * 5
    offshore_ratio = five_year_total / old_aum if old_aum > 0 else 0

    return ActionResult(
        updated_properties={
            "cross_border_need": "HIGH",
            "offshore_demand_ratio": round(offshore_ratio, 4),
            "estimated_annual_outflow": annual_cost,
        },
        old_values={
            "cross_border_need": ctx.target_node.get("cross_border_need", "LOW"),
        },
    )


@register_action
def pb_divorce_asset_impact(ctx: ActionContext) -> ActionResult:
    """Assess trust asset impact from a divorce event.

    L2 function that estimates the potential impact on family trust assets
    during a divorce proceeding, considering trust protection mechanisms
    and potential asset split ratios.

    Params:
        split_ratio (float): Expected asset split ratio (default 0.5)
    """
    split_ratio = ctx.params.get("split_ratio", 0.5)
    old_scale = ctx.target_node.get("scale", 0)
    # Family trusts typically protect ~70% of assets from divorce claims
    protection_rate = 0.7
    at_risk = old_scale * (1 - protection_rate)
    potential_loss = at_risk * split_ratio
    new_scale = old_scale - potential_loss

    return ActionResult(
        updated_properties={
            "scale": new_scale,
            "status": "UNDER_REVIEW",
            "at_risk_amount": at_risk,
            "protection_rate": protection_rate,
        },
        old_values={
            "scale": old_scale,
            "status": ctx.target_node.get("status", "ACTIVE"),
        },
    )


# ---------------------------------------------------------------------------
# L3 Intelligence Layer — Graph-Aware Private Banking Analytics
# ---------------------------------------------------------------------------

@register_action
def pb_concentration_risk_check(ctx: ActionContext) -> ActionResult:
    """Analyze portfolio concentration risk by traversing graph topology.

    L3 intelligence function that examines the client's entire investment
    graph — including direct holdings, portfolio investments, and controlled
    entities — to determine if any single entity represents a dangerously
    large share of total AUM. Critical after IPO events when a single
    stock may dominate the portfolio.

    Params:
        threshold (float): Concentration warning threshold (default 0.4 = 40%)
    """
    graph = ctx.graph
    target_id = ctx.target_id
    threshold = ctx.params.get("threshold", 0.4)

    total_aum = ctx.target_node.get("aum", 0)
    if total_aum <= 0:
        return ActionResult(
            updated_properties={"concentration_risk": "UNKNOWN"},
            old_values={},
        )

    # Traverse: Customer -> HAS_PORTFOLIO -> Portfolio -> INVESTED_IN -> Entity
    max_single_exposure = 0
    max_entity_name = ""

    for _, portfolio_id, edata in graph.out_edges(target_id, data=True):
        if edata.get("type") != "HAS_PORTFOLIO":
            continue
        # Examine investments from this portfolio
        for _, entity_id, inv_data in graph.out_edges(portfolio_id, data=True):
            if inv_data.get("type") == "INVESTED_IN":
                amount = inv_data.get("amount", 0)
                if amount > max_single_exposure:
                    max_single_exposure = amount
                    entity_attrs = graph.nodes.get(entity_id, {})
                    max_entity_name = entity_attrs.get("name", entity_id)

    # Also check direct control relationships (equity in controlled entities)
    for _, biz_id, edata in graph.out_edges(target_id, data=True):
        if edata.get("type") == "CONTROLS":
            equity_pct = edata.get("equity_pct", 0)
            biz_attrs = graph.nodes.get(biz_id, {})
            biz_valuation = biz_attrs.get("valuation", 0)
            equity_value = biz_valuation * equity_pct
            if equity_value > max_single_exposure:
                max_single_exposure = equity_value
                max_entity_name = biz_attrs.get("name", biz_id)

    concentration = max_single_exposure / total_aum if total_aum > 0 else 0
    risk_level = (
        "HIGH" if concentration > threshold
        else "MODERATE" if concentration > threshold * 0.6
        else "LOW"
    )

    return ActionResult(
        updated_properties={
            "concentration_risk": risk_level,
            "max_single_exposure": max_single_exposure,
            "max_exposure_entity": max_entity_name,
            "concentration_ratio": round(concentration, 4),
        },
        old_values={
            "concentration_risk": ctx.target_node.get("concentration_risk", "UNKNOWN"),
        },
    )


@register_action
def pb_detect_competitor_threat(ctx: ActionContext) -> ActionResult:
    """Detect competitor threat level by analyzing the competitive graph topology.

    L3 intelligence function that examines all competitor edges targeting
    this client, assesses each competitor's intensity and strategy, and
    factors in the triggering event type (some events like IPO success or
    banker departure amplify competitive pressure significantly).

    Params:
        event_type (str): The triggering event that may attract competitors
    """
    graph = ctx.graph
    target_id = ctx.target_id
    event_type = ctx.params.get("event_type", "UNKNOWN")

    intensity_scores = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "VERY_HIGH": 4}
    competitor_count = 0
    total_intensity = 0

    # Find all competitors targeting this client
    for u, _v, edata in graph.in_edges(target_id, data=True):
        if edata.get("type") == "TARGETS":
            competitor_count += 1
            comp_attrs = graph.nodes.get(u, {})
            intensity = comp_attrs.get("intensity", edata.get("intensity", "MEDIUM"))
            total_intensity += intensity_scores.get(intensity, 2)

    # Different events amplify competitor threat differently
    threat_multiplier = {
        "IPO_SUCCESS": 1.5,       # IPO success makes client highly attractive
        "PRODUCT_MATURITY": 1.3,  # Product maturity creates switching window
        "BANKER_CHANGE": 1.8,     # Banker departure creates vulnerability
        "COMPETITOR_RAID": 2.0,   # Direct competitor action
    }.get(event_type, 1.0)

    threat_score = total_intensity * threat_multiplier
    threat_level = (
        "CRITICAL" if threat_score >= 8
        else "HIGH" if threat_score >= 5
        else "MODERATE" if threat_score >= 3
        else "LOW"
    )

    return ActionResult(
        updated_properties={
            "competitor_threat": threat_level,
            "competitor_count": competitor_count,
            "threat_score": round(threat_score, 2),
        },
        old_values={
            "competitor_threat": ctx.target_node.get("competitor_threat", "UNKNOWN"),
        },
    )


@register_action
def pb_compute_churn_risk(ctx: ActionContext) -> ActionResult:
    """Compute client churn risk based on service relationship and competitive landscape.

    L3 intelligence function that combines multiple graph-derived signals:
    - Service relationship depth (banker tenure reduces risk)
    - Competitive pressure (number and intensity of competing institutions)
    - Event-triggered vulnerability windows

    Produces a calibrated churn probability and risk classification.

    Params:
        base_risk (float): Base churn probability before adjustments (0-1)
        tenure_factor (float): Risk reduction per year of banker service
        competitive_factor (float): Additional risk per active competitor
    """
    graph = ctx.graph
    target_id = ctx.target_id
    base_risk = ctx.params.get("base_risk", 0.2)
    tenure_factor = ctx.params.get("tenure_factor", 0.03)
    competitive_factor = ctx.params.get("competitive_factor", 0.1)

    # Find current private banker and their tenure
    banker_tenure = 0
    for _, banker_id, edata in graph.out_edges(target_id, data=True):
        if edata.get("type") == "SERVED_BY":
            banker_attrs = graph.nodes.get(banker_id, {})
            banker_tenure = banker_attrs.get("years_served", 0)
            # If banker has already departed, tenure protection is zero
            if banker_attrs.get("status") == "DEPARTED":
                banker_tenure = 0
            break

    # Tenure reduces risk (deeper relationship = more sticky)
    tenure_reduction = banker_tenure * tenure_factor

    # Competitor count and intensity increases risk
    competitor_pressure = 0
    for u, _v, edata in graph.in_edges(target_id, data=True):
        if edata.get("type") == "TARGETS":
            competitor_pressure += competitive_factor

    churn_risk = min(1.0, max(0.0, base_risk - tenure_reduction + competitor_pressure))

    risk_label = (
        "CRITICAL" if churn_risk >= 0.5
        else "HIGH" if churn_risk >= 0.35
        else "MODERATE" if churn_risk >= 0.2
        else "LOW"
    )

    return ActionResult(
        updated_properties={
            "churn_risk": round(churn_risk, 4),
            "churn_risk_level": risk_label,
        },
        old_values={
            "churn_risk": ctx.target_node.get("churn_risk", 0),
        },
    )


@register_action
def pb_assess_retention_action(ctx: ActionContext) -> ActionResult:
    """Assess and recommend client retention actions based on customer value and risk.

    L3 intelligence function that evaluates the client's AUM tier to determine
    the appropriate retention budget and action level. Higher-value clients
    receive proportionally larger retention investments.

    Params:
        urgency (str): Action urgency level (NORMAL, HIGH, IMMEDIATE)
    """
    urgency = ctx.params.get("urgency", "NORMAL")
    aum = ctx.target_node.get("aum", 0)

    # Determine retention tier and budget based on AUM
    if aum >= 100_000_000:   # ¥1亿+: Platinum tier
        retention_level = "PLATINUM"
        budget_ratio = 0.001   # 0.1% of AUM
    elif aum >= 30_000_000:  # ¥3000万+: Gold tier
        retention_level = "GOLD"
        budget_ratio = 0.0005  # 0.05% of AUM
    else:                     # Below ¥3000万: Silver tier
        retention_level = "SILVER"
        budget_ratio = 0.0002  # 0.02% of AUM

    retention_budget = aum * budget_ratio

    return ActionResult(
        updated_properties={
            "retention_priority": urgency,
            "retention_level": retention_level,
            "retention_budget": retention_budget,
        },
        old_values={
            "retention_priority": ctx.target_node.get("retention_priority", "NORMAL"),
        },
    )
