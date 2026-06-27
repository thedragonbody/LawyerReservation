import { create } from 'zustand';
import Cookies from 'js-cookie';
import { authApi } from './api';

export type UserRole = 'lawyer' | 'customer';

interface User {
  id: string;
  phone: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: UserRole;
  is_phone_verified: boolean;
  is_staff: boolean;
  is_superuser?: boolean;
  avatar_url: string | null;
}

interface AuthState {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  setUser: (user: User | null) => void;
  setTokens: (access: string, refresh: string) => void;
  logout: () => Promise<void>;
  fetchMe: () => Promise<void>;
}

const cookieOptions = {
  secure: process.env.NODE_ENV === 'production',
  sameSite: 'lax' as const,
  path: '/',
};

export const getDashboardPath = (role?: UserRole | string | null, isStaff?: boolean) =>
  isStaff ? '/dashboard/admin' : role === 'lawyer' ? '/dashboard/lawyer' : '/dashboard/customer';

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isLoading: false,
  isAuthenticated: false,

  setUser: (user) => set({ user, isAuthenticated: !!user }),

  setTokens: (access, refresh) => {
    Cookies.set('access_token', access, { ...cookieOptions, expires: 1 });
    Cookies.set('refresh_token', refresh, { ...cookieOptions, expires: 30 });
  },

  fetchMe: async () => {
    const token = Cookies.get('access_token');
    if (!token) return;
    set({ isLoading: true });
    try {
      const { data } = await authApi.me();
      set({ user: data, isAuthenticated: true });
    } catch {
      Cookies.remove('access_token', { path: '/' });
      Cookies.remove('refresh_token', { path: '/' });
      set({ user: null, isAuthenticated: false });
    } finally {
      set({ isLoading: false });
    }
  },

  logout: async () => {
    const refresh = Cookies.get('refresh_token');
    if (refresh) {
      try { await authApi.logout(refresh); } catch {}
    }
    Cookies.remove('access_token', { path: '/' });
    Cookies.remove('refresh_token', { path: '/' });
    set({ user: null, isAuthenticated: false });
    window.location.href = '/';
  },
}));
