/**
 * Order & Payment Service
 * Handles order queries, status auditing, and real-time reconciliation.
 */

import { apiClient } from './apiClient';

export interface OrderItem {
  order_id: string;
  _id?: string;
  user_id: string;
  tour_id: string;
  tour_title?: string;
  amount_vnd: number;
  currency: string;
  status: string;
  customer_name?: string;
  customer_phone?: string;
  created_at: string;
  expires_at?: string;
  paid_at?: string;
}

export const orderService = {
  /**
   * Lists orders (handles both admin endpoint and general orders endpoint).
   */
  async getOrders(statusFilter?: string, skip = 0, limit = 50): Promise<OrderItem[]> {
    try {
      const data = await apiClient.get<OrderItem[]>('/payments/admin/orders', {
        params: { status: statusFilter, skip, limit },
      });
      return Array.isArray(data) ? data : [];
    } catch {
      // Fallback to /orders endpoint
      const fallback = await apiClient.get<OrderItem[]>('/orders', {
        params: { status: statusFilter, skip, limit },
      });
      return Array.isArray(fallback) ? fallback : [];
    }
  },

  /**
   * Triggers direct reconciliation with payment gateway (VNPAY / payOS).
   */
  async reconcileOrder(orderId: string): Promise<any> {
    try {
      return await apiClient.post<any>(`/payments/admin/orders/${orderId}/reconcile`);
    } catch {
      return await apiClient.post<any>(`/orders/${orderId}/reconcile`);
    }
  },
};
