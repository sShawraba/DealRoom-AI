import axios from "axios";

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api/v1",
  timeout: 30000,
});

// Attach JWT to every request if token is present in the store.
apiClient.interceptors.request.use((config) => {
  // Lazy-import to avoid circular deps; store is synchronous.
  const stored = JSON.parse(
    localStorage.getItem("dealroom-auth") || "{}"
  );
  const token = stored?.state?.token;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// On 401 — clear auth state and redirect to login.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("dealroom-auth");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default apiClient;
