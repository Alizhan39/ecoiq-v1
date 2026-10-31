import { api } from './client';
import type { ProjectList } from '@/types/projects';

export function listProjects(signal?: AbortSignal): Promise<ProjectList> {
  return api.get<ProjectList>('/projects/', signal);
}
