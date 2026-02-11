"""Action functions covering L1 (Data), L2 (Information), and L3 (Intelligence) layers.

All functions follow the uniform signature: (ctx: ActionContext) -> ActionResult
"""

from app.engine.action_registry import ActionContext, ActionResult, register_action


# ---------------------------------------------------------------------------
# L1 Data Layer
# ---------------------------------------------------------------------------

@register_action
def set_property(ctx: ActionContext) -> ActionResult:
    """Set a node property to a new value. Returns the old value.

    Params:
        property (str): Name of the property to update.
        value (Any): New value to assign.
    """
    prop = ctx.params["property"]
    value = ctx.params["value"]
    old_value = ctx.target_node.get(prop)
    return ActionResult(
        updated_properties={prop: value},
        old_values={prop: old_value},
    )


@register_action
def adjust_numeric(ctx: ActionContext) -> ActionResult:
    """Multiply a numeric property by a factor. Returns old and new values.

    Params:
        property (str): Name of the numeric property.
        factor (float): Multiplicative factor to apply.
    """
    prop = ctx.params["property"]
    factor = ctx.params["factor"]
    old_value = ctx.target_node.get(prop, 0)
    new_value = old_value * factor
    return ActionResult(
        updated_properties={prop: new_value},
        old_values={prop: old_value},
    )


@register_action
def update_risk_status(ctx: ActionContext) -> ActionResult:
    """Update the risk status field of a node.

    Params:
        status (str): New risk status value (e.g. 'HIGH_RISK', 'LOW_RISK').
    """
    new_status = ctx.params.get("status", "HIGH_RISK")
    old_status = ctx.target_node.get("risk_status")
    return ActionResult(
        updated_properties={"risk_status": new_status},
        old_values={"risk_status": old_status},
    )


# ---------------------------------------------------------------------------
# L2 Information Layer
# ---------------------------------------------------------------------------

@register_action
def recalculate_valuation(ctx: ActionContext) -> ActionResult:
    """Recalculate valuation as old_val * (1 + shock_factor). Returns old and new valuations.

    Params:
        shock_factor (float): Percentage change expressed as a decimal (e.g. -0.3 for -30%).
    """
    old_val = ctx.target_node.get("valuation", 0)
    shock_factor = ctx.params.get("shock_factor", 0)
    new_val = old_val * (1 + shock_factor)
    return ActionResult(
        updated_properties={"valuation": new_val},
        old_values={"valuation": old_val},
    )


@register_action
def compute_margin_gap(ctx: ActionContext) -> ActionResult:
    """Compute margin gap: loan_amount * (1 - collateral_ratio * (1 + stock_change)).

    Reads loan_amount and collateral_ratio from the target node properties,
    and stock_change from params.

    Params:
        stock_change (float): Stock price change as a decimal (e.g. -0.4 for -40%).
    """
    loan_amount = ctx.target_node.get("loan_amount", 0)
    collateral_ratio = ctx.target_node.get("collateral_ratio", 1.0)
    stock_change = ctx.params.get("stock_change", 0)
    margin_gap = loan_amount * (1 - collateral_ratio * (1 + stock_change))
    return ActionResult(
        updated_properties={"margin_gap": margin_gap},
        old_values={"loan_amount": loan_amount, "collateral_ratio": collateral_ratio},
    )


# ---------------------------------------------------------------------------
# L3 Intelligence Layer
# ---------------------------------------------------------------------------

@register_action
def graph_weighted_exposure(ctx: ActionContext) -> ActionResult:
    """Traverse graph topology and compute weighted exposure along edges.

    Walks neighbors of the target node filtered by direction and edge_type,
    computing: aggregate(neighbor_value * edge_weight) with support for
    sum, max, and count aggregation modes.

    Params:
        direction (str): 'in', 'out', or 'both'. Default 'out'.
        edge_type (str | None): Filter edges by this type. None = all edges.
        value_property (str): Neighbor node property to use as value. Default 'valuation'.
        weight_property (str): Edge property to use as weight. Default 'weight'.
        aggregation (str): 'sum', 'max', or 'count'. Default 'sum'.
    """
    graph = ctx.graph
    target_id = ctx.target_id
    direction = ctx.params.get("direction", "out")
    edge_type = ctx.params.get("edge_type")
    value_property = ctx.params.get("value_property", "valuation")
    weight_property = ctx.params.get("weight_property", "weight")
    aggregation = ctx.params.get("aggregation", "sum")

    edges = []
    if direction in ("in", "both"):
        edges.extend(graph.in_edges(target_id, data=True))
    if direction in ("out", "both"):
        edges.extend(graph.out_edges(target_id, data=True))

    total = 0.0
    max_val = 0.0
    count = 0

    for u, v, data in edges:
        if edge_type and data.get("type") != edge_type:
            continue
        neighbor_id = v if u == target_id else u
        neighbor_attrs = graph.nodes.get(neighbor_id, {})
        neighbor_value = neighbor_attrs.get(value_property, 0)
        edge_weight = data.get(weight_property, 1.0)
        weighted = neighbor_value * edge_weight

        total += weighted
        if weighted > max_val:
            max_val = weighted
        count += 1

    if aggregation == "max":
        result_value = max_val
    elif aggregation == "count":
        result_value = count
    else:
        result_value = total

    old_exposure = ctx.target_node.get("exposure", 0)
    return ActionResult(
        updated_properties={"exposure": result_value},
        old_values={"exposure": old_exposure},
    )
