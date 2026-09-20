/**
 * QR Code Service
 * Manages opaque QR generation, direct client audio routing, activation, and removal.
 */

import { apiClient } from './apiClient';

export interface QRCodeItem {
  id: string;
  _id?: string;
  code: string;
  target_type?: 'poi' | 'tour';
  poi_id?: string;
  tour_id?: string;
  target_name?: string;
  poi_name?: string;
  location_description?: string;
  is_active: boolean;
  created_at?: string;
}

export interface QRCreateData {
  target_type?: 'poi' | 'tour';
  poi_id?: string;
  tour_id?: string;
  code: string;
  location_description?: string;
}

export const qrService = {
  /**
   * Lists all QR codes registered in the system.
   */
  async getQRCodes(params: { skip?: number; limit?: number } = {}): Promise<QRCodeItem[]> {
    const data = await apiClient.get<QRCodeItem[]>('/qr', {
      params: {
        skip: params.skip || 0,
        limit: params.limit || 100,
      },
    });
    return Array.isArray(data) ? data : [];
  },

  /**
   * Generates a new QR code associated with a POI.
   */
  async createQRCode(payload: QRCreateData): Promise<QRCodeItem> {
    return apiClient.post<QRCodeItem>('/qr', payload);
  },

  /**
   * Activates / re-enables a deactivated QR code.
   */
  async activateQRCode(qrId: string): Promise<any> {
    return apiClient.post<any>(`/qr/${qrId}/activate`);
  },

  /**
   * Deactivates a QR code without deleting it.
   */
  async deactivateQRCode(qrId: string): Promise<any> {
    return apiClient.post<any>(`/qr/${qrId}/deactivate`);
  },

  /**
   * Permanently deletes a QR code.
   */
  async deleteQRCode(qrId: string): Promise<void> {
    return apiClient.delete<void>(`/qr/${qrId}`);
  },
};
