import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore, getDashboardRouteForRole } from "../stores/auth";

import LoginView from "../views/LoginView.vue";
import RegisterView from "../views/RegisterView.vue";
import AdminDashboard from "../views/AdminDashboard.vue";
import ExaminerDashboard from "../views/ExaminerDashboard.vue";
import StudentDashboard from "../views/StudentDashboard.vue";

const routes = [
  {
    path: "/",
    redirect: "/login",
  },
  {
    path: "/login",
    name: "Login",
    component: LoginView,
    meta: { guestOnly: true },
  },
  {
    path: "/register",
    name: "Register",
    component: RegisterView,
    meta: { guestOnly: true },
  },
  {
    path: "/admin/dashboard",
    name: "AdminDashboard",
    component: AdminDashboard,
    meta: { requiresAuth: true, role: "Admin" },
  },
  {
    path: "/examiner/dashboard",
    name: "ExaminerDashboard",
    component: ExaminerDashboard,
    meta: { requiresAuth: true, role: "Examiner" },
  },
  {
    path: "/student/dashboard",
    name: "StudentDashboard",
    component: StudentDashboard,
    meta: { requiresAuth: true, role: "Student" },
  },
  {
    path: "/:pathMatch(.*)*",
    redirect: "/login",
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

/**
 * Navigation Guard (RBAC):
 * 1. Redirect unauthenticated users to /login when accessing protected routes.
 * 2. Redirect already-authenticated users away from guest-only pages (/login, /register) to their dashboard.
 * 3. Inspect to.meta.role: if the user's role does not match the route, redirect them to their respective dashboard.
 */
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore();
  const isAuthenticated = authStore.isAuthenticated;
  const userRole = authStore.role;

  // Protected route check
  if (to.meta.requiresAuth || to.meta.role) {
    if (!isAuthenticated) {
      return next({ name: "Login", query: { redirect: to.fullPath } });
    }

    if (to.meta.role && to.meta.role !== userRole) {
      const targetDashboard = getDashboardRouteForRole(userRole);
      return next(targetDashboard);
    }
  }

  // Prevent authenticated users from seeing Login/Register unless they log out
  if (to.meta.guestOnly && isAuthenticated) {
    const targetDashboard = getDashboardRouteForRole(userRole);
    return next(targetDashboard);
  }

  return next();
});

export default router;

