<template>
  <div class="container py-5">
    <div class="row justify-content-center">
      <div class="col-12 col-md-7 col-lg-5">
        <div class="card shadow-sm border-0">
          <div class="card-header bg-success text-white text-center py-3">
            <h4 class="mb-0 fw-semibold">Student Registration</h4>
            <small class="text-white-50">
              Self-registration is exclusively for Students
            </small>
          </div>

          <div class="card-body p-4">
            <div class="alert alert-info py-2 small" role="alert">
              <strong>Note:</strong> Examiners and Administrators cannot self-register.
              Examiner accounts are provisioned by the Portal Administrator.
            </div>

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

            <form @submit.prevent="handleRegister" novalidate>
              <div class="mb-3">
                <label for="name" class="form-label fw-medium">Full Name</label>
                <input
                  id="name"
                  v-model.trim="name"
                  type="text"
                  class="form-control"
                  placeholder="Enter your full name"
                  required
                  :disabled="loading"
                />
              </div>

              <div class="mb-3">
                <label for="email" class="form-label fw-medium">Email Address</label>
                <input
                  id="email"
                  v-model.trim="email"
                  type="email"
                  class="form-control"
                  placeholder="student@portal.com"
                  required
                  autocomplete="email"
                  :disabled="loading"
                />
              </div>

              <div class="mb-3">
                <label for="password" class="form-label fw-medium">Password</label>
                <input
                  id="password"
                  v-model="password"
                  type="password"
                  class="form-control"
                  placeholder="Minimum 6 characters"
                  required
                  autocomplete="new-password"
                  :disabled="loading"
                />
              </div>

              <div class="mb-4">
                <label for="confirmPassword" class="form-label fw-medium">
                  Confirm Password
                </label>
                <input
                  id="confirmPassword"
                  v-model="confirmPassword"
                  type="password"
                  class="form-control"
                  placeholder="Re-enter your password"
                  required
                  autocomplete="new-password"
                  :disabled="loading"
                />
              </div>

              <div class="d-grid">
                <button
                  type="submit"
                  class="btn btn-success btn-lg"
                  :disabled="loading"
                >
                  <span
                    v-if="loading"
                    class="spinner-border spinner-border-sm me-2"
                    role="status"
                    aria-hidden="true"
                  ></span>
                  {{ loading ? "Creating Account..." : "Register as Student" }}
                </button>
              </div>
            </form>
          </div>

          <div class="card-footer bg-white text-center py-3">
            <span class="text-muted">Already have an account?</span>
            <router-link to="/login" class="ms-1 fw-semibold text-decoration-none">
              Sign In
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

const name = ref("");
const email = ref("");
const password = ref("");
const confirmPassword = ref("");
const loading = ref(false);
const errorMessage = ref("");

async function handleRegister() {
  errorMessage.value = "";

  if (!name.value || !email.value || !password.value) {
    errorMessage.value = "All fields (Name, Email, Password) are required.";
    return;
  }

  if (password.value.length < 6) {
    errorMessage.value = "Password must be at least 6 characters long.";
    return;
  }

  if (password.value !== confirmPassword.value) {
    errorMessage.value = "Passwords do not match.";
    return;
  }

  loading.value = true;
  try {
    const user = await authStore.registerStudent({
      name: name.value,
      email: email.value,
      password: password.value,
    });
    const targetRoute = getDashboardRouteForRole(user.role);
    await router.push(targetRoute);
  } catch (err) {
    errorMessage.value =
      err.response?.data?.message ||
      "Registration failed. Please check your details and try again.";
  } finally {
    loading.value = false;
  }
}
</script>

