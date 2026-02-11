import { useEffect, useRef, useCallback } from 'react';
import { Graph, NodeEvent, CanvasEvent } from '@antv/g6';
import type { NodeData, EdgeData, IElementEvent } from '@antv/g6';
import { useWorkspace } from '../../hooks/useWorkspace';

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

export function GraphCanvas() {
  const { state, dispatch } = useWorkspace();
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<Graph | null>(null);

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

  // When selectedNodeId changes, update element states for highlight
  useEffect(() => {
    const graph = graphRef.current;
    if (!graph) return;

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
