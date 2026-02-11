import { useEffect, useRef, useCallback } from 'react';
import { Graph, NodeEvent, CanvasEvent } from '@antv/g6';
import type { NodeData, EdgeData, IElementEvent } from '@antv/g6';
import { useWorkspace } from '../../hooks/useWorkspace';
import type { PendingSimulation } from '../../hooks/useWorkspace';
import type { SimulateResponse } from '../../types';

const RIPPLE_STEP_DELAY = 500; // ms between each ripple step

/** Map ontology shape names to G6 v5 built-in node types */
function mapShape(shape: string): string {
  switch (shape.toLowerCase()) {
    case 'diamond':
      return 'diamond';
    case 'rect':
    case 'rectangle':
      return 'rect';
    case 'triangle':
      return 'triangle';
    case 'star':
      return 'star';
    case 'hexagon':
      return 'hexagon';
    case 'ellipse':
      return 'ellipse';
    default:
      return 'circle';
  }
}

/**
 * Find edge IDs from the G6 graph that connect nodes in the highlight_edges list.
 * highlight_edges from backend contain source/target info.
 */
function findHighlightEdgeIds(
  edgeData: EdgeData[],
  highlightEdges: SimulateResponse['delta_graph']['highlight_edges'],
): string[] {
  const edgeIds: string[] = [];
  for (const he of highlightEdges) {
    const src = he.source as string;
    const tgt = he.target as string;
    const matched = edgeData.find(
      (e) =>
        (e.source === src && e.target === tgt) ||
        (e.source === tgt && e.target === src),
    );
    if (matched?.id) {
      edgeIds.push(matched.id as string);
    }
  }
  return edgeIds;
}

export function GraphCanvas() {
  const { state, dispatch } = useWorkspace();
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);
  const animatingRef = useRef(false);

  // Keep latest dispatch/state in refs so event handlers always see current values
  const dispatchRef = useRef(dispatch);
  dispatchRef.current = dispatch;

  const ontologyDefRef = useRef(state.ontologyDef);
  ontologyDefRef.current = state.ontologyDef;

  const graphDataRef = useRef(state.graphData);
  graphDataRef.current = state.graphData;

  // Build G6 data from workspace graphData
  const buildG6Data = useCallback(() => {
    const gd = graphDataRef.current;
    const od = ontologyDefRef.current;
    if (!gd || !od) return null;

    const nodes: NodeData[] = gd.nodes.map((n) => ({
      id: n.id,
      data: {
        nodeType: n.type,
        label: (n.properties?.name as string) || n.id,
        ...n.properties,
      },
    }));

    const edges: EdgeData[] = gd.edges.map((e, i) => ({
      id: `edge-${e.source}-${e.target}-${e.type}-${i}`,
      source: e.source,
      target: e.target,
      data: {
        edgeType: e.type,
        ...e.properties,
      },
    }));

    return { nodes, edges };
  }, []);

  // Create graph on mount
  useEffect(() => {
    if (!containerRef.current) return;

    const graph = new Graph({
      container: containerRef.current,
      autoResize: true,
      autoFit: 'view',
      padding: 40,

      node: {
        type: (datum: NodeData) => {
          const od = ontologyDefRef.current;
          const nodeType = datum.data?.nodeType as string;
          const typeDef = od?.node_types?.[nodeType];
          return typeDef ? mapShape(typeDef.shape) : 'circle';
        },
        style: (datum: NodeData) => {
          const od = ontologyDefRef.current;
          const nodeType = datum.data?.nodeType as string;
          const typeDef = od?.node_types?.[nodeType];
          const color = typeDef?.color || '#999';

          return {
            size: 36,
            fill: color,
            stroke: '#fff',
            lineWidth: 2,
            cursor: 'pointer',
            labelText: (datum.data?.label as string) || datum.id,
            labelPlacement: 'bottom' as const,
            labelFontSize: 11,
            labelFill: '#333',
            labelBackground: true,
            labelBackgroundFill: 'rgba(255,255,255,0.85)',
            labelBackgroundRadius: 3,
            labelPadding: [1, 4, 1, 4],
            labelOffsetY: 4,
          };
        },
        state: {
          selected: {
            stroke: '#ff4d4f',
            lineWidth: 3,
            halo: true,
            haloStroke: '#ff4d4f',
            haloStrokeOpacity: 0.25,
            haloLineWidth: 8,
          },
          inactive: {
            opacity: 0.35,
          },
          rippleActive: {
            stroke: '#ff7a45',
            lineWidth: 4,
            halo: true,
            haloStroke: '#ff7a45',
            haloStrokeOpacity: 0.4,
            haloLineWidth: 12,
            size: 48,
          },
          rippleVisited: {
            stroke: '#ff4d4f',
            lineWidth: 3,
            halo: true,
            haloStroke: '#ff4d4f',
            haloStrokeOpacity: 0.2,
            haloLineWidth: 6,
          },
          rippleDimmed: {
            opacity: 0.3,
          },
        },
      },

      edge: {
        type: 'line',
        style: (datum: EdgeData) => {
          const od = ontologyDefRef.current;
          const edgeType = datum.data?.edgeType as string;
          const typeDef = od?.edge_types?.[edgeType];
          const color = typeDef?.color || '#c0c0c0';
          const isDashed = typeDef?.style === 'dashed';

          return {
            stroke: color,
            lineWidth: 1.5,
            lineDash: isDashed ? [4, 4] : undefined,
            endArrow: true,
            endArrowFill: color,
            endArrowSize: 6,
            labelText: typeDef?.label || '',
            labelFontSize: 9,
            labelFill: '#999',
            labelBackground: true,
            labelBackgroundFill: 'rgba(255,255,255,0.8)',
            labelBackgroundRadius: 2,
            labelPadding: [0, 3, 0, 3],
          };
        },
        state: {
          inactive: {
            strokeOpacity: 0.15,
          },
          rippleHighlight: {
            stroke: '#ff4d4f',
            lineWidth: 3,
            endArrowFill: '#ff4d4f',
          },
          rippleDimmed: {
            strokeOpacity: 0.15,
          },
        },
      },

      layout: {
        type: 'd3-force',
        preventOverlap: true,
        nodeSize: 40,
        manyBody: { strength: -200 },
        link: { distance: 140, strength: 0.4 },
        collide: { radius: 30, strength: 0.8 },
      },

      behaviors: ['drag-canvas', 'zoom-canvas', 'drag-element'],
      animation: true,
    });

    graphRef.current = graph;

    // Node click: select the node
    graph.on(NodeEvent.CLICK, (event: IElementEvent) => {
      // Ignore clicks during animation
      if (animatingRef.current) return;

      const nodeId = event.target.id;
      // Find node type from current graphData
      const gd = graphDataRef.current;
      const node = gd?.nodes.find((n) => n.id === nodeId);
      const nodeType = node?.type || '';

      dispatchRef.current({
        type: 'SELECT_NODE',
        payload: { nodeId, nodeType },
      });
    });

    // Canvas click: deselect
    graph.on(CanvasEvent.CLICK, () => {
      if (animatingRef.current) return;
      dispatchRef.current({ type: 'DESELECT_NODE' });
    });

    return () => {
      graph.destroy();
      graphRef.current = null;
    };
  }, []); // mount once

  // When graphData or ontologyDef changes, reload data into graph
  useEffect(() => {
    const graph = graphRef.current;
    if (!graph) return;

    const data = buildG6Data();
    if (!data) return;

    graph.setData(data);
    graph.render();
  }, [state.graphData, state.ontologyDef, buildG6Data]);

  // When selectedNodeId changes (and not animating), update element states for highlight
  useEffect(() => {
    const graph = graphRef.current;
    if (!graph || animatingRef.current) return;

    // Ensure graph has rendered data
    let nodeData: NodeData[];
    let edgeData: EdgeData[];
    try {
      nodeData = graph.getNodeData();
      edgeData = graph.getEdgeData();
    } catch {
      return; // graph not ready yet
    }

    if (nodeData.length === 0) return;

    const stateMap: Record<string, string | string[]> = {};
    const selectedId = state.selectedNodeId;

    if (selectedId) {
      // Highlight selected node, dim others
      nodeData.forEach((n) => {
        stateMap[n.id] = n.id === selectedId ? 'selected' : 'inactive';
      });
      edgeData.forEach((e) => {
        if (!e.id) return;
        const related = e.source === selectedId || e.target === selectedId;
        stateMap[e.id] = related ? [] : 'inactive';
      });
    } else {
      // Clear all states
      nodeData.forEach((n) => {
        stateMap[n.id] = [];
      });
      edgeData.forEach((e) => {
        if (!e.id) return;
        stateMap[e.id] = [];
      });
    }

    graph.setElementState(stateMap);
  }, [state.selectedNodeId]);

  // Play ripple animation when pendingSimulation is set
  useEffect(() => {
    const pending = state.pendingSimulation;
    if (!pending) return;

    const graph = graphRef.current;
    if (!graph) {
      // No graph, skip animation and finalize immediately
      dispatchRef.current({
        type: 'SIMULATE_DONE',
        payload: pending,
      });
      return;
    }

    // Start animation
    playRippleAnimation(graph, pending);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [state.pendingSimulation]);

  const playRippleAnimation = useCallback(
    async (graph: Graph, pending: PendingSimulation) => {
      animatingRef.current = true;

      const { response, actionId, displayName } = pending;
      const { ripple_path, delta_graph } = response;

      let nodeData: NodeData[];
      let edgeData: EdgeData[];
      try {
        nodeData = graph.getNodeData();
        edgeData = graph.getEdgeData();
      } catch {
        // Graph not ready, finalize immediately
        animatingRef.current = false;
        dispatchRef.current({
          type: 'SIMULATE_DONE',
          payload: { response, actionId, displayName },
        });
        return;
      }

      if (nodeData.length === 0 || ripple_path.length === 0) {
        animatingRef.current = false;
        dispatchRef.current({
          type: 'SIMULATE_DONE',
          payload: { response, actionId, displayName },
        });
        return;
      }

      // Build set of ripple node IDs and highlight edge IDs
      const rippleNodeSet = new Set(ripple_path);
      const highlightEdgeIds = findHighlightEdgeIds(
        edgeData,
        delta_graph.highlight_edges,
      );
      const highlightEdgeSet = new Set(highlightEdgeIds);

      // Step 1: Dim all non-ripple nodes/edges
      const initialStateMap: Record<string, string | string[]> = {};
      nodeData.forEach((n) => {
        initialStateMap[n.id] = rippleNodeSet.has(n.id)
          ? []
          : 'rippleDimmed';
      });
      edgeData.forEach((e) => {
        if (!e.id) return;
        initialStateMap[e.id] = highlightEdgeSet.has(e.id as string)
          ? []
          : 'rippleDimmed';
      });
      graph.setElementState(initialStateMap);

      // Step 2: Animate along the ripple path node by node
      const visitedNodes: string[] = [];

      for (let i = 0; i < ripple_path.length; i++) {
        const nodeId = ripple_path[i];
        // Check if this node exists in the graph
        const nodeExists = nodeData.some((n) => n.id === nodeId);
        if (!nodeExists) continue;

        await delay(RIPPLE_STEP_DELAY);

        // Set current node to rippleActive, previous nodes to rippleVisited
        const stepStateMap: Record<string, string | string[]> = {};

        // Dimmed non-ripple nodes stay dimmed
        nodeData.forEach((n) => {
          if (!rippleNodeSet.has(n.id)) {
            stepStateMap[n.id] = 'rippleDimmed';
          }
        });

        // Mark visited nodes
        for (const vn of visitedNodes) {
          stepStateMap[vn] = 'rippleVisited';
        }

        // Mark current node as active
        stepStateMap[nodeId] = 'rippleActive';

        // Unvisited ripple nodes remain default
        for (const rn of ripple_path) {
          if (rn !== nodeId && !visitedNodes.includes(rn) && !stepStateMap[rn]) {
            stepStateMap[rn] = [];
          }
        }

        // Highlight edges connected to current node that are in highlight set
        edgeData.forEach((e) => {
          if (!e.id) return;
          if (highlightEdgeSet.has(e.id as string)) {
            // Highlight edge if it connects a visited/current node to the current node
            const connectedToCurrent =
              e.source === nodeId || e.target === nodeId;
            const connectedToVisited =
              visitedNodes.includes(e.source as string) ||
              visitedNodes.includes(e.target as string);
            if (connectedToCurrent && (connectedToVisited || i === 0)) {
              stepStateMap[e.id] = 'rippleHighlight';
            } else if (!stepStateMap[e.id]) {
              stepStateMap[e.id] = [];
            }
          } else {
            stepStateMap[e.id] = 'rippleDimmed';
          }
        });

        graph.setElementState(stepStateMap);
        visitedNodes.push(nodeId);
      }

      // Step 3: Brief pause showing all ripple nodes as visited
      await delay(RIPPLE_STEP_DELAY);

      // Step 4: Apply final state - updated nodes get their new visual status
      // Build a set of updated node IDs from delta_graph
      const updatedNodeIds = new Set(
        delta_graph.updated_nodes.map((n) => n.id as string).filter(Boolean),
      );

      // Final state: all ripple nodes show rippleVisited, non-ripple cleared
      const finalStateMap: Record<string, string | string[]> = {};
      nodeData.forEach((n) => {
        if (rippleNodeSet.has(n.id) || updatedNodeIds.has(n.id)) {
          finalStateMap[n.id] = 'rippleVisited';
        } else {
          finalStateMap[n.id] = [];
        }
      });
      edgeData.forEach((e) => {
        if (!e.id) return;
        if (highlightEdgeSet.has(e.id as string)) {
          finalStateMap[e.id] = 'rippleHighlight';
        } else {
          finalStateMap[e.id] = [];
        }
      });
      graph.setElementState(finalStateMap);

      // Animation complete — dispatch SIMULATE_DONE
      animatingRef.current = false;
      dispatchRef.current({
        type: 'SIMULATE_DONE',
        payload: { response, actionId, displayName },
      });
    },
    [],
  );

  // Show placeholder if no data loaded
  if (!state.graphData) {
    return (
      <div className="panel-placeholder">
        请上传 JSON 文件或选择内置示例加载图谱
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{ width: '100%', height: '100%' }}
    />
  );
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
