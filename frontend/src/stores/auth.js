import { defineStore } from "pinia";
import { ref, computed } from "vue";
import apiClient from "../services/api";

export const ROLE_DASHBOARD_MAP = {
  Admin: "/admin/dashboard",
  Examiner: "/examiner/dashboard",
  Student: "/student/dashboard",
};

export function getDashboardRouteForRole(role) {
  return ROLE_DASHBOARD_MAP[role] || "/login";
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref(localStorage.getItem("portal_token") || null);
  const role = ref(localStorage.getItem("portal_role") || null);
  const user = ref(
    (() => {
      try {
        const raw = localStorage.getItem("portal_user");
        return raw ? JSON.parse(raw) : null;
      } catch {
        return null;
      }
    })()
  );

  const isAuthenticated = computed(() => Boolean(token.value && role.value));

  function setSession(newToken, userObj) {
    token.value = newToken;
    role.value = userObj?.role || null;
    user.value = userObj || null;

    if (newToken) {
      localStorage.setItem("portal_token", newToken);
    } else {
      localStorage.removeItem("portal_token");
    }

    if (userObj?.role) {
      localStorage.setItem("portal_role", userObj.role);
    } else {
      localStorage.removeItem("portal_role");
    }

    if (userObj) {
      localStorage.setItem("portal_user", JSON.stringify(userObj));
    } else {
      localStorage.removeItem("portal_user");
    }
  }

  function logout() {
    setSession(null, null);
  }

  async function login(email, password) {
    const response = await apiClient.post("/api/auth/login", {
      email,
      password,
    });
    const accessToken = response.data.access_token || response.data.token;
    const userData = response.data.user;
    setSession(accessToken, userData);
    return userData;
  }

  async function registerStudent({ name, email, password }) {
    const response = await apiClient.post("/api/auth/register", {
      name,
      email,
      password,
      role: "Student",
    });
    const accessToken = response.data.access_token || response.data.token;
    const userData = response.data.user;
    setSession(accessToken, userData);
    return userData;
  }

  async function fetchCurrentUser() {
    if (!token.value) return null;
    try {
      const response = await apiClient.get("/api/auth/me");
      if (response.data?.user) {
        setSession(token.value, response.data.user);
      }
      return response.data.user;
    } catch (error) {
      logout();
      throw error;
    }
  }

  return {
    token,
    role,
    user,
    isAuthenticated,
    setSession,
    login,
    registerStudent,
    fetchCurrentUser,
    logout,
  };
});

