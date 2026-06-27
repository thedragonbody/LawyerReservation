import axios from 'axios';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
});

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = Cookies.get('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = Cookies.get('refresh_token');
      if (refresh) {
        try {
          const { data } = await axios.post(`${API_URL}/auth/token/refresh/`, { refresh });
          Cookies.set('access_token', data.access, { expires: 1, sameSite: 'lax', secure: process.env.NODE_ENV === 'production', path: '/' });
          original.headers.Authorization = `Bearer ${data.access}`;
          return api(original);
        } catch {
          Cookies.remove('access_token');
          Cookies.remove('refresh_token');
          if (typeof window !== 'undefined') window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// ─── Auth ──────────────────────────────────────────────────────────────────────
export const authApi = {
  register: (data: any) => api.post('/auth/register/', data),
  adminLogin: (phone: string, password: string) => api.post('/auth/admin-login/', { phone, password }),
  requestOtp: (phone: string) => api.post('/auth/request-otp/', { phone }),
  verifyOtp: (phone: string, otp: string) => api.post('/auth/verify-otp/', { phone, otp }),
  resendOtp: (phone: string) => api.post('/otp/resend/', { phone }),
  me: () => api.get('/auth/me/'),
  updateMe: (data: any) => api.patch('/auth/me/update/', data),
  logout: (refresh: string) => api.post('/auth/logout/', { refresh }),
};

// ─── Lawyers ──────────────────────────────────────────────────────────────────
export const lawyerApi = {
  list: (params?: any) => api.get('/lawyers/', { params }),
  detail: (id: string) => api.get(`/lawyers/${id}/`),
  myProfile: () => api.get('/lawyers/me/profile/'),
  updateProfile: (data: any) => api.patch('/lawyers/me/profile/', data, data instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined),
  dashboard: () => api.get('/lawyers/me/dashboard/'),
  availabilityDay: (date: string) => api.get('/lawyers/me/availability/day/', { params: { date } }),
  saveAvailabilityDay: (data: any) => api.post('/lawyers/me/availability/day/', data),
  addReview: (lawyerId: string, data: any) => api.post(`/lawyers/${lawyerId}/reviews/`, data),
  slots: (lawyerId: string, date: string) =>
    api.get(`/bookings/slots/${lawyerId}/`, { params: { date } }),
  justiveAnalyze: (message: string) => api.post('/lawyers/justive/analyze/', { message }),
};

// ─── Bookings ─────────────────────────────────────────────────────────────────
export const bookingApi = {
  list: () => api.get('/bookings/'),
  lawyerBookings: (status?: string) =>
    api.get('/bookings/lawyer/', { params: status ? { status } : {} }),
  create: (data: any) => api.post('/bookings/', data),
  detail: (id: string) => api.get(`/bookings/${id}/`),
  update: (id: string, data: any) => api.patch(`/bookings/${id}/`, data),
  cancel: (id: string, reason?: string) => api.post(`/bookings/${id}/cancel/`, { reason: reason || '' }),
  uploadDocument: (bookingId: string, formData: FormData) =>
    api.post(`/bookings/${bookingId}/documents/`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  deleteDocument: (bookingId: string, docId: string) =>
    api.delete(`/bookings/${bookingId}/documents/${docId}/`),
  getDocuments: (bookingId: string) => api.get(`/bookings/${bookingId}/documents/`),
};

// ─── Customer Dashboard ───────────────────────────────────────────────────────
export const customerApi = {
  dashboard: () => api.get('/customers/dashboard/'),
};


// ─── Admin Panel ──────────────────────────────────────────────────────────────
export const adminApi = {
  overview: () => api.get('/admin-panel/overview/'),
  users: (params?: any) => api.get('/admin-panel/users/', { params }),
  updateUser: (id: string, data: any) => api.patch(`/admin-panel/users/${id}/`, data),
  lawyers: (params?: any) => api.get('/admin-panel/lawyers/', { params }),
  lawyerDetail: (id: string) => api.get(`/admin-panel/lawyers/${id}/`),
  updateLawyer: (id: string, data: any) => api.patch(`/admin-panel/lawyers/${id}/`, data),
  verifyLawyer: (id: string, status: 'verified' | 'rejected' | 'pending') =>
    api.post(`/admin-panel/lawyers/${id}/verify/`, { status }),
  bookings: (params?: any) => api.get('/admin-panel/bookings/', { params }),
  updateBooking: (id: string, data: any) => api.patch(`/admin-panel/bookings/${id}/`, data),
  documents: (params?: any) => api.get('/admin-panel/documents/', { params }),
  reviews: (params?: any) => api.get('/admin-panel/reviews/', { params }),
  updateReview: (id: string, data: any) => api.patch(`/admin-panel/reviews/${id}/`, data),
  deleteReview: (id: string) => api.delete(`/admin-panel/reviews/${id}/`),
  revenue: () => api.get('/admin-panel/revenue/'),
  financeOverview: () => api.get('/admin-panel/finance-overview/'),
  commission: () => api.get('/admin-panel/commission/'),
  updateCommission: (data: any) => api.post('/admin-panel/commission/', data),
  discounts: (params?: any) => api.get('/admin-panel/discounts/', { params }),
  createDiscount: (data: any) => api.post('/admin-panel/discounts/', data),
  updateDiscount: (id: string, data: any) => api.patch(`/admin-panel/discounts/${id}/`, data),
  settlements: (params?: any) => api.get('/admin-panel/settlements/', { params }),
  createSettlement: (data: any) => api.post('/admin-panel/settlements/', data),
  updateSettlement: (id: string, data: any) => api.patch(`/admin-panel/settlements/${id}/`, data),
  cancellations: (params?: any) => api.get('/admin-panel/cancellations/', { params }),
  siteContent: () => api.get('/admin-panel/site-content/'),
  updateSiteContent: (data: any) => api.post('/admin-panel/site-content/', data),
};

// ─── Smart MVP helpers ────────────────────────────────────────────────────────
export const walletApi = {
  summary: () => api.get('/bookings/wallet/summary/'),
};
