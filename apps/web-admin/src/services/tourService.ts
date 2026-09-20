/**
 * Tour Service
 * Handles tour creation, ordered POI stops, pricing configuration, and tour lifecycle.
 */

import { apiClient } from './apiClient';

export interface TourStop {
  poi_id: string;
  stop_order: number;
}

export interface Tour {
  id: string;
  _id?: string;
  code: string;
  name: string;
  title?: string;
  description: string;
  poi_count: number;
  poi_ids: string[];
  pois?: any[];
  stops?: TourStop[];
  price_amount: number;
  price_vnd?: number;
  currency: string;
  is_paid: boolean;
  for_sale: boolean;
  is_purchasable: boolean;
  is_active: boolean;
  version?: number;
  created_at?: string;
  updated_at?: string;
}

export interface TourCreateData {
  name: string;
  description?: string;
  poi_ids: string[];
  price_amount?: number;
  price_vnd?: number;
  currency?: string;
  is_paid?: boolean;
  is_purchasable?: boolean;
  is_active?: boolean;
}

export interface TourUpdateData {
  name?: string;
  description?: string;
  poi_ids?: string[];
  price_amount?: number;
  price_vnd?: number;
  currency?: string;
  is_paid?: boolean;
  is_purchasable?: boolean;
  is_active?: boolean;
  expected_version?: number;
}

export interface TourPricingData {
  price_amount: number;
  price_vnd?: number;
  currency?: string;
  is_purchasable: boolean;
  for_sale?: boolean;
  is_paid?: boolean;
  preview_enabled?: boolean;
  preview_poi_ids?: string[];
}

export const tourService = {
  /**
   * Lists all public tours.
   */
  async getTours(params: { skip?: number; limit?: number } = {}): Promise<Tour[]> {
    const data = await apiClient.get<Tour[]>('/tours', {
      params: {
        skip: params.skip || 0,
        limit: params.limit || 50,
      },
    });
    return Array.isArray(data) ? data : [];
  },

  /**
   * Retrieves tour detail with ordered stops and POI items.
   */
  async getTourDetail(tourId: string, lang = 'vi'): Promise<Tour> {
    return apiClient.get<Tour>(`/tours/${tourId}`, { params: { lang } });
  },

  /**
   * Creates a new tour with ordered stops.
   */
  async createTour(payload: TourCreateData): Promise<Tour> {
    return apiClient.post<Tour>('/tours', payload);
  },

  /**
   * Updates tour details (name, description, ordered stops).
   */
  async updateTour(tourId: string, payload: TourUpdateData): Promise<Tour> {
    return apiClient.put<Tour>(`/tours/${tourId}`, payload);
  },

  /**
   * Updates tour pricing policy and sales availability.
   */
  async updateTourPricing(tourId: string, payload: TourPricingData): Promise<any> {
    return apiClient.put<any>(`/tours/${tourId}/pricing`, payload);
  },

  /**
   * Soft deletes a tour.
   */
  async deleteTour(tourId: string): Promise<void> {
    return apiClient.delete<void>(`/tours/${tourId}`);
  },
};
