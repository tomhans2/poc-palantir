import { createContext, useContext, useReducer, type Dispatch } from 'react';
import type {
  Metadata,
  OntologyDef,
  GraphData,
  Action,
  InsightItem,
  SimulateResponse,
  RegisteredFunction,
} from '../types';

// ---- State ----

export interface SimulationHistoryEntry {
  actionId: string;
  displayName: string;
  timestamp: string;
  insights: InsightItem[];
  ripplePath: string[];
}

export interface PendingSimulation {
  response: SimulateResponse;
  actionId: string;
  displayName: string;
}

export interface WorkspaceState {
  metadata: Metadata | null;
  ontologyDef: OntologyDef | null;
  graphData: GraphData | null;
  actions: Action[];
  selectedNodeId: string | null;
  selectedNodeType: string | null;
  insights: InsightItem[];
  isSimulating: boolean;
  simulationHistory: SimulationHistoryEntry[];
  pendingSimulation: PendingSimulation | null;
  warnings: string[];
  registeredFunctions: RegisteredFunction[];
}

export const initialState: WorkspaceState = {
  metadata: null,
  ontologyDef: null,
  graphData: null,
  actions: [],
  selectedNodeId: null,
  selectedNodeType: null,
  insights: [],
  isSimulating: false,
  simulationHistory: [],
  pendingSimulation: null,
  warnings: [],
  registeredFunctions: [],
};

// ---- Actions ----

export type WorkspaceAction =
  | {
      type: 'LOAD_WORKSPACE';
      payload: {
        metadata: Metadata;
        ontologyDef: OntologyDef;
        graphData: GraphData;
        actions: Action[];
        warnings?: string[];
        registeredFunctions?: RegisteredFunction[];
      };
    }
  | {
      type: 'SELECT_NODE';
      payload: { nodeId: string; nodeType: string };
    }
  | { type: 'DESELECT_NODE' }
  | { type: 'SIMULATE_START' }
  | {
      type: 'SIMULATE_RESPONSE_RECEIVED';
      payload: {
        response: SimulateResponse;
        actionId: string;
        displayName: string;
      };
    }
  | {
      type: 'SIMULATE_DONE';
      payload: {
        response: SimulateResponse;
        actionId: string;
        displayName: string;
      };
    }
  | { type: 'RESET'; payload?: { graphData: GraphData } };

// ---- Reducer ----

export function workspaceReducer(
  state: WorkspaceState,
  action: WorkspaceAction,
): WorkspaceState {
  switch (action.type) {
    case 'LOAD_WORKSPACE':
      return {
        ...initialState,
        metadata: action.payload.metadata,
        ontologyDef: action.payload.ontologyDef,
        graphData: action.payload.graphData,
        actions: action.payload.actions,
        warnings: action.payload.warnings ?? [],
        registeredFunctions: action.payload.registeredFunctions ?? [],
      };

    case 'SELECT_NODE':
      return {
        ...state,
        selectedNodeId: action.payload.nodeId,
        selectedNodeType: action.payload.nodeType,
      };

    case 'DESELECT_NODE':
      return {
        ...state,
        selectedNodeId: null,
        selectedNodeType: null,
      };

    case 'SIMULATE_START':
      return {
        ...state,
        isSimulating: true,
      };

    case 'SIMULATE_RESPONSE_RECEIVED': {
      const { response, actionId, displayName } = action.payload;
      return {
        ...state,
        isSimulating: true,
        pendingSimulation: { response, actionId, displayName },
      };
    }

    case 'SIMULATE_DONE': {
      const { response, actionId, displayName } = action.payload;
      const entry: SimulationHistoryEntry = {
        actionId,
        displayName,
        timestamp: new Date().toISOString(),
        insights: response.insights,
        ripplePath: response.ripple_path,
      };
      return {
        ...state,
        isSimulating: false,
        pendingSimulation: null,
        insights: [...state.insights, ...response.insights],
        simulationHistory: [...state.simulationHistory, entry],
        // Update graphData with latest node properties from backend
        graphData: response.updated_graph_data ?? state.graphData,
      };
    }

    case 'RESET':
      return {
        ...state,
        selectedNodeId: null,
        selectedNodeType: null,
        insights: [],
        isSimulating: false,
        simulationHistory: [],
        pendingSimulation: null,
        graphData: action.payload?.graphData ?? state.graphData,
      };

    default:
      return state;
  }
}

// ---- Context ----

export interface WorkspaceContextValue {
  state: WorkspaceState;
  dispatch: Dispatch<WorkspaceAction>;
}

export const WorkspaceContext = createContext<WorkspaceContextValue | null>(
  null,
);

// ---- Hook ----

export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return ctx;
}

// ---- Provider helper (returns props for context provider) ----

export function useWorkspaceReducer() {
  return useReducer(workspaceReducer, initialState);
}
