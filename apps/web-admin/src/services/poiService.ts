/**
 * POI Service
 * Handles CRUD operations, GPS validation, audio recording & Google TTS synthesis,
 * 6-language auto-translation, and publication readiness gates.
 */

import { apiClient } from './apiClient';

export interface GeoLocation {
  type: string;
  coordinates: [number, number]; // [lng, lat]
}

export interface POI {
  id: string;
  _id?: string;
  name: string;
  description: string;
  category: string;
  address?: string;
  location: GeoLocation;
  images?: string[];
  trigger_radius: number;
  audio_priority: number;
  audio_url?: string | null;
  audio_duration_ms?: number;
  audio_status?: string;
  is_active: boolean;
  activation_requested?: boolean;
  translations?: Record<string, any>;
  published_contents?: Record<string, any>;
  version?: number;
  created_at?: string;
  updated_at?: string;
}

export interface POICreateData {
  name: string;
  description: string;
  category: string;
  address?: string;
  location: GeoLocation;
  images?: string[];
  trigger_radius: number;
  audio_priority: number;
  audio_url?: string | null;
  audio_duration_ms?: number;
  auto_translate?: boolean;
  activation_requested?: boolean;
}

export interface POIUpdateData {
  id?: string;
  name?: string;
  description?: string;
  category?: string;
  address?: string;
  location?: GeoLocation;
  images?: string[];
  trigger_radius?: number;
  audio_priority?: number;
  audio_url?: string | null;
  audio_duration_ms?: number;
  auto_translate?: boolean;
  expected_version?: number;
}

export interface POIListParams {
  search?: string;
  category?: string;
  lang?: string;
  skip?: number;
  limit?: number;
}

export interface POIListResponse {
  items: POI[];
  total: number;
  page?: number;
  pages?: number;
  skip?: number;
  limit?: number;
}

export interface TTSSynthesizeResponse {
  status: string;
  audio_url: string;
  audio_duration_ms: number;
  text_length: number;
  provider: string;
}

export interface AIRefineDescriptionResponse {
  poi_name: string;
  refined_description: string;
  suggested_title?: string;
  highlights: string[];
  narration_script?: string;
}

export interface AIMultilingualItem {
  name: string;
  description: string;
}

export interface AIMultilingualTranslateResponse {
  poi_id?: string;
  translations: Record<string, AIMultilingualItem>;
}

export interface POIAssistantResponse {
  name: string;
  category: string;
  address: string;
  description: string;
  narration_script: string;
  specialties: string[];
  latitude?: number;
  longitude?: number;
  confidence?: string;
}

export const poiService = {
  /**
   * Retrieves paginated list of POIs with search and category filtering.
   */
  async getPOIs(params: POIListParams = {}): Promise<POIListResponse> {
    const data = await apiClient.get<any>('/pois', {
      params: {
        search: params.search,
        category: params.category,
        lang: params.lang || 'vi',
        skip: params.skip || 0,
        limit: params.limit || 100,
      },
    });

    if (data && Array.isArray(data.items)) {
      return {
        items: data.items,
        total: data.total ?? data.items.length,
        page: data.page,
        pages: data.pages,
        skip: data.skip,
        limit: data.limit,
      };
    }
    if (Array.isArray(data)) {
      return { items: data, total: data.length };
    }
    return { items: [], total: 0 };
  },

  /**
   * Fetches POI detail by ID.
   */
  async getPOIDetail(id: string, lang = 'vi'): Promise<POI> {
    return apiClient.get<POI>(`/pois/${id}`, { params: { lang } });
  },

  /**
   * Creates a new POI draft with optional audio and automated 6-language translation.
   */
  async createPOI(payload: POICreateData): Promise<POI> {
    return apiClient.post<POI>('/pois', payload);
  },

  /**
   * Updates POI with optimistic concurrency control and auto-sync.
   */
  async updatePOI(id: string, payload: POIUpdateData): Promise<POI> {
    const targetUrl = id ? `/pois/${id}` : '/pois';
    return apiClient.put<POI>(targetUrl, { ...payload, id });
  },

  /**
   * Soft deletes a POI (sets deleted_at, is_active=False).
   */
  async deletePOI(id: string): Promise<void> {
    return apiClient.delete<void>(`/pois/${id}`);
  },

  /**
   * Toggles publication state with Readiness Gate check.
   */
  async toggleActive(id: string, active: boolean): Promise<any> {
    return apiClient.post<any>(`/pois/${id}/toggle-active?active=${active}`);
  },

  /**
   * Forces automated 6-language translation and Google TTS generation for a single POI.
   */
  async syncMultilingual(id: string): Promise<any> {
    return apiClient.post<any>(`/pois/${id}/sync-multilingual`);
  },

  /**
   * Batch synchronizes 6-language translations and Google TTS audio across all POIs.
   */
  async batchSyncAll(): Promise<any> {
    return apiClient.post<any>('/pois/batch-sync-all');
  },

  /**
   * Synthesizes speech from text using Google TTS (vietnamese standard narration).
   */
  async synthesizeGoogleTTS(text: string, lang = 'vi'): Promise<TTSSynthesizeResponse> {
    return apiClient.post<TTSSynthesizeResponse>('/audio/synthesize-text', {
      text,
      lang,
      provider: 'google',
    });
  },

  /**
   * Uploads custom MP3 audio narration file for a POI.
   */
  async uploadAudio(id: string, file: File, lang = 'vi'): Promise<{ audio_url: string; audio_duration_ms: number }> {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.upload<{ audio_url: string; audio_duration_ms: number }>(
      `/audio/upload/${id}?lang=${lang}`,
      formData
    );
  },

  /**
   * Refines or enriches a POI description into an enticing travel narrative using Gemini AI.
   */
  async refineDescription(params: {
    poi_name: string;
    current_description?: string;
    category?: string;
    address?: string;
    tone?: string;
  }): Promise<AIRefineDescriptionResponse> {
    return apiClient.post<AIRefineDescriptionResponse>('/ai/refine-description', params);
  },

  /**
   * Generates GPS audio narration script using Gemini AI.
   */
  async generateNarration(params: {
    poi_name: string;
    category?: string;
    address?: string;
    specialties?: string[];
    tone?: string;
    weather?: string;
    language_code?: string;
  }): Promise<{ title: string; description: string; narration_text: string; suggested_voice: string }> {
    return apiClient.post<any>('/ai/generate-narration', params);
  },

  /**
   * Translates POI into 6 languages (VI, EN, FR, JA, KO, ZH) using Gemini AI cultural adaptation.
   */
  async translateMultilingualGemini(params: {
    poi_id?: string;
    poi_name: string;
    description: string;
    category?: string;
  }): Promise<AIMultilingualTranslateResponse> {
    return apiClient.post<AIMultilingualTranslateResponse>('/ai/multilingual-translate', params);
  },

  /**
   * Recognizes restaurant or landmark name and auto-generates description, address, category, narration script, specialties, and GPS coordinates using Gemini AI.
   */
  async poiAssistant(params: {
    poi_name: string;
    address_hint?: string;
    category_hint?: string;
    context?: string;
  }): Promise<POIAssistantResponse> {
    return apiClient.post<POIAssistantResponse>('/ai/poi-assistant', params);
  },
};
