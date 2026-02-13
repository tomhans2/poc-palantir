import axios from 'axios';
import type { LoadResponse, SimulateResponse, SampleInfo, GraphData } from '../types';

const api = axios.create({
  baseURL: '/api/v1/workspace',
});

/**
 * Load workspace from file upload or built-in sample name.
 *
 * Accepts either:
 * - A built-in sample name (string)
 * - A JSON config file, optionally paired with a Python action file
 */
export async function loadWorkspace(
  fileOrSample: File | string,
  actionFile?: File,
): Promise<LoadResponse> {
  if (typeof fileOrSample === 'string') {
    // Load built-in sample by name
    const { data } = await api.post<LoadResponse>('/load', null, {
      params: { sample: fileOrSample },
    });
    return data;
  }
  // File upload — JSON config + optional Python action file
  const formData = new FormData();
  formData.append('file', fileOrSample);
  if (actionFile) {
    formData.append('action_file', actionFile);
  }
  const { data } = await api.post<LoadResponse>('/load', formData);
  return data;
}

/**
 * Execute a simulation action on a target node.
 */
export async function simulate(
  actionId: string,
  nodeId: string,
): Promise<SimulateResponse> {
  const { data } = await api.post<SimulateResponse>('/simulate', {
    action_id: actionId,
    node_id: nodeId,
  });
  return data;
}

/**
 * Reset the workspace to its initial state.
 */
export async function resetWorkspace(): Promise<GraphData> {
  const { data } = await api.post<GraphData>('/reset');
  return data;
}

/**
 * Get simulation event history.
 */
export async function getHistory(): Promise<unknown[]> {
  const { data } = await api.get<unknown[]>('/history');
  return data;
}

/**
 * Get the list of available built-in sample files.
 */
export async function getSamples(): Promise<SampleInfo[]> {
  const { data } = await api.get<SampleInfo[]>('/samples');
  return data;
}
