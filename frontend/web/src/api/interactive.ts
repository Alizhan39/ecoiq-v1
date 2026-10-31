import { api } from './client';

export type Language = 'en' | 'ru' | 'kk' | 'ar';
export interface Hotspot {
  id: string;
  label: string;
  position: string;
  normal: string;
  evidence_url: string | null;
  measurement: number | null;
}
export interface Scene {
  id: string;
  language: Language;
  direction: 'rtl' | 'ltr';
  is_demo: boolean;
  verified: boolean;
  model_url: string;
  ar_modes: string[];
  hotspots: Hotspot[];
}
export const getScene = (language: Language, signal?: AbortSignal) =>
  api.get<Scene>(`/interactive/scenes/stewardship-demo/?lang=${language}`, signal);

export interface Library {
  id: string;
  name: string;
  category: 'ui' | 'ar';
  purpose: string;
  documentation_url: string;
  status: 'INTEGRATED' | 'OPTION';
}
export const getLibraries = (signal: AbortSignal) =>
  api.get<{ count: number; results: Library[] }>('/interactive/libraries/', signal);
