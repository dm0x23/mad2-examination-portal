<template>
  <div class="container py-5">
    <div class="row justify-content-center">
      <div class="col-12 col-md-7 col-lg-5">
        <div class="card shadow-sm border-0">
          <div class="card-header bg-primary text-white text-center py-3">
            <h4 class="mb-0 fw-semibold">Examination Management Portal</h4>
            <small class="text-white-50">Sign in to your account</small>
          </div>

          <div class="card-body p-4">
            <div
              v-if="errorMessage"
              class="alert alert-danger alert-dismissible fade show"
              role="alert"
            >
              {{ errorMessage }}
              <button
                type="button"
                class="btn-close"
                aria-label="Close"
                @click="errorMessage = ''"
              ></button>
            </div>

            <form @submit.prevent="handleLogin" novalidate>
              <div class="mb-3">
                <label for="email" class="form-label fw-medium">Email Address</label>
                <input
                  id="email"
                  v-model.trim="email"
                  type="email"
                  class="form-control"
                  placeholder="name@portal.com"
                  required
                  autocomplete="email"
                  :disabled="loading"
                />
              </div>

              <div class="mb-4">
                <label for="password" class="form-label fw-medium">Password</label>
                <input
                  id="password"
                  v-model="password"
                  type="password"
                  class="form-control"
                  placeholder="Enter your password"
                  required
                  autocomplete="current-password"
                  :disabled="loading"
                />
              </div>

              <div class="d-grid">
                <button
                  type="submit"
                  class="btn btn-primary btn-lg"
                  :disabled="loading"
                >
                  <span
                    v-if="loading"
                    class="spinner-border spinner-border-sm me-2"
                    role="status"
                    aria-hidden="true"
                  ></span>
                  {{ loading ? "Signing in..." : "Sign In" }}
                </button>
              </div>
            </form>
          </div>

          <div class="card-footer bg-white text-center py-3">
            <span class="text-muted">Are you a student without an account?</span>
            <router-link to="/register" class="ms-1 fw-semibold text-decoration-none">
              Register as Student
            </router-link>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore, getDashboardRouteForRole } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const email = ref("");
const password = ref("");
const loading = ref(false);
const errorMessage = ref("");

async function handleLogin() {
  errorMessage.value = "";

  if (!email.value || !password.value) {
    errorMessage.value = "Please enter both email and password.";
    return;
  }

  loading.value = true;
  try {
    const user = await authStore.login(email.value, password.value);
    const targetRoute = getDashboardRouteForRole(user.role);
    await router.push(targetRoute);
  } catch (err) {
    errorMessage.value =
      err.response?.data?.message ||
      "Failed to sign in. Please check your credentials.";
  } finally {
    loading.value = false;
  }
}
</script>

