import type { ReactNode } from 'react';
import {
  WorkspaceContext,
  useWorkspaceReducer,
} from '../hooks/useWorkspace';

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useWorkspaceReducer();

  return (
    <WorkspaceContext value={{ state, dispatch }}>
      {children}
    </WorkspaceContext>
  );
}
