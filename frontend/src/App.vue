<template>
  <div class="min-vh-100 d-flex flex-column bg-light">
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark shadow-sm">
      <div class="container">
        <router-link class="navbar-brand fw-bold" to="/">
          ExamPortal V2
        </router-link>

        <div class="d-flex align-items-center ms-auto">
          <template v-if="authStore.isAuthenticated">
            <span class="navbar-text text-light me-3 small">
              {{ authStore.user?.email }}
              <span class="badge bg-secondary ms-1">{{ authStore.role }}</span>
            </span>
            <button
              class="btn btn-sm btn-outline-light"
              type="button"
              @click="handleLogout"
            >
              Logout
            </button>
          </template>
          <template v-else>
            <router-link to="/login" class="btn btn-sm btn-outline-light me-2">
              Login
            </router-link>
            <router-link to="/register" class="btn btn-sm btn-primary">
              Student Register
            </router-link>
          </template>
        </div>
      </div>
    </nav>

    <main class="flex-grow-1">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { useRouter } from "vue-router";
import { useAuthStore } from "./stores/auth";

const router = useRouter();
const authStore = useAuthStore();

function handleLogout() {
  authStore.logout();
  router.push("/login");
}
</script>

