import { useCallback } from 'react';
import { simulate } from '../services/api';
import { useWorkspace } from './useWorkspace';

export function useSimulation() {
  const { state, dispatch } = useWorkspace();

  const onSimulate = useCallback(
    async (actionId: string) => {
      const { selectedNodeId, actions } = state;
      if (!selectedNodeId) return;

      const action = actions.find((a) => a.action_id === actionId);
      const displayName = action?.display_name ?? actionId;

      dispatch({ type: 'SIMULATE_START' });
      try {
        const response = await simulate(actionId, selectedNodeId);
        dispatch({
          type: 'SIMULATE_DONE',
          payload: { response, actionId, displayName },
        });
        return response;
      } catch (error) {
        // On error, stop simulating state but don't add results
        dispatch({
          type: 'SIMULATE_DONE',
          payload: {
            response: {
              status: 'error',
              delta_graph: { updated_nodes: [], highlight_edges: [] },
              ripple_path: [],
              insights: [],
            },
            actionId,
            displayName,
          },
        });
        throw error;
      }
    },
    [state, dispatch],
  );

  return { onSimulate, isSimulating: state.isSimulating };
}
