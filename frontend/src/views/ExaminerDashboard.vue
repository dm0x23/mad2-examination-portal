<template>
  <div class="container py-4">
    <div class="card shadow-sm border-0">
      <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center py-3">
        <div>
          <h4 class="mb-0">Examiner Dashboard</h4>
          <small class="text-white-50">Examination Management Portal V2</small>
        </div>
        <span class="badge bg-warning text-dark fs-6">Role: {{ authStore.role }}</span>
      </div>

      <div class="card-body p-4">
        <p class="lead mb-3">
          Welcome, <strong>{{ authStore.user?.email }}</strong>!
        </p>
        <p class="text-muted">
          This is the placeholder Examiner Dashboard for Milestone 2 (Authentication &amp; RBAC verification).
        </p>

        <div class="d-flex flex-wrap gap-2 mt-4">
          <button
            class="btn btn-outline-primary"
            :disabled="pingLoading"
            @click="verifyExaminerPing"
          >
            Test GET /api/examiner/ping
          </button>
          <button class="btn btn-outline-danger ms-auto" @click="handleLogout">
            Logout
          </button>
        </div>

        <div v-if="pingResult" class="alert alert-success mt-3 mb-0">
          <strong>RBAC Ping Response:</strong>
          <pre class="mb-0 mt-1 small">{{ JSON.stringify(pingResult, null, 2) }}</pre>
        </div>
        <div v-if="pingError" class="alert alert-danger mt-3 mb-0">
          {{ pingError }}
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import apiClient from "../services/api";

const router = useRouter();
const authStore = useAuthStore();

const pingLoading = ref(false);
const pingResult = ref(null);
const pingError = ref("");

async function verifyExaminerPing() {
  pingLoading.value = true;
  pingResult.value = null;
  pingError.value = "";
  try {
    const response = await apiClient.get("/api/examiner/ping");
    pingResult.value = response.data;
  } catch (err) {
    pingError.value =
      err.response?.data?.message || "Failed to reach /api/examiner/ping";
  } finally {
    pingLoading.value = false;
  }
}

function handleLogout() {
  authStore.logout();
  router.push("/login");
}
</script>

