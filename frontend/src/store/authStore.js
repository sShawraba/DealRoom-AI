import { create } from "zustand";
import { persist } from "zustand/middleware";

function decodeJwt(token) {
  try {
    const base64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    const payload = JSON.parse(atob(base64));
    return { id: payload.sub, role: payload.role, email: payload.email, full_name: payload.full_name, tenant_id: payload.tenant_id };
  } catch {
    return null;
  }
}

const useAuthStore = create(
  persist(
    (set) => ({
      token: null,
      user: null,
      setAuth: (token, _user) => set({ token, user: decodeJwt(token) }),
      logout: () => set({ token: null, user: null }),
    }),
    {
      name: "dealroom-auth",
    }
  )
);

export default useAuthStore;
