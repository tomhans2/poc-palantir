// ---- Ontology Definition ----

export interface NodeTypeDef {
  label: string;
  color: string;
  shape: string;
  icon?: string;
  properties?: Record<string, unknown>;
}

export interface EdgeTypeDef {
  label: string;
  color: string;
  style?: string;
  properties?: Record<string, unknown>;
}

export interface OntologyDef {
  node_types: Record<string, NodeTypeDef>;
  edge_types: Record<string, EdgeTypeDef>;
}

// ---- Graph Data ----

export interface GraphNode {
  id: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  properties: Record<string, unknown>;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// ---- Action Definitions ----

export interface DirectEffect {
  property_to_update: string;
  new_value: unknown;
}

export interface EffectOnTarget {
  action_to_trigger: string;
  parameters: Record<string, unknown>;
}

export interface RippleRule {
  rule_id: string;
  propagation_path: string;
  condition?: string;
  effect_on_target: EffectOnTarget;
  insight_template?: string;
  insight_type?: string;
  insight_severity?: string;
}

export interface Action {
  action_id: string;
  target_node_type: string;
  display_name: string;
  direct_effect?: DirectEffect;
  ripple_rules: RippleRule[];
}

export interface ActionEngine {
  actions: Action[];
}

// ---- Workspace ----

export interface Metadata {
  domain: string;
  version?: string;
  description?: string;
}

export interface WorkspaceConfig {
  metadata: Metadata;
  ontology_def: OntologyDef;
  graph_data: GraphData;
  action_engine: ActionEngine;
}

// ---- API Types ----

export type InsightType =
  | 'event_trigger'
  | 'risk_propagation'
  | 'quantitative_impact'
  | 'network_analysis'
  | 'recommendation';

export type InsightSeverity = 'info' | 'warning' | 'critical';

export interface InsightItem {
  text: string;
  type: InsightType;
  severity: InsightSeverity;
  source_node?: string;
  target_node?: string;
  rule_id?: string;
}

export interface DeltaGraph {
  updated_nodes: Record<string, unknown>[];
  highlight_edges: Record<string, unknown>[];
}

export interface SimulateResponse {
  status: string;
  delta_graph: DeltaGraph;
  ripple_path: string[];
  insights: InsightItem[];
}

export interface RegisteredFunction {
  name: string;
  source: string;
}

export interface LoadResponse {
  metadata: Metadata;
  ontology_def: OntologyDef;
  graph_data: GraphData;
  actions: Action[];
  registered_functions: RegisteredFunction[];
  warnings: string[];
}

export interface SampleInfo {
  name: string;
  description: string;
}
