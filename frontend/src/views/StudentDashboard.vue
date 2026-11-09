<template>
  <div class="container-fluid py-4 px-md-4">
    <!-- Header -->
    <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
      <div>
        <h2 class="h3 fw-bold mb-1 text-dark">Student Portal</h2>
        <p class="text-muted mb-0 small">
          Examination Management Portal V2 &bull; Logged in as
          <span class="fw-semibold text-primary">{{ authStore.user?.email }}</span>
          <span class="badge bg-success ms-2">Student</span>
        </p>
      </div>
      <div class="d-flex gap-2 mt-2 mt-sm-0">
        <button
          class="btn btn-outline-secondary btn-sm d-flex align-items-center"
          :disabled="loading"
          @click="refreshAllData"
        >
          <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
          <span>&#x21bb; Refresh</span>
        </button>
        <button class="btn btn-outline-danger btn-sm" @click="handleLogout">
          Logout
        </button>
      </div>
    </div>

    <!-- Alert Notifications -->
    <div
      v-if="alertMessage.text"
      :class="['alert', 'alert-' + alertMessage.type, 'alert-dismissible', 'fade', 'show', 'shadow-sm']"
      role="alert"
    >
      <strong>{{ alertMessage.type === 'danger' ? 'Error: ' : 'Success: ' }}</strong>
      {{ alertMessage.text }}
      <button
        type="button"
        class="btn-close"
        aria-label="Close"
        @click="clearAlert"
      ></button>
    </div>

    <!-- Summary Metrics Cards -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-primary border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Available Exams</span>
            <h3 class="fw-bold my-1 text-primary">{{ metrics.available_exams_count }}</h3>
            <small class="text-muted">Open for slot reservation</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-warning border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Active Bookings</span>
            <h3 class="fw-bold my-1 text-warning">{{ metrics.active_bookings_count }}</h3>
            <small class="text-muted">Upcoming examinations</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-success border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Completed Exams</span>
            <h3 class="fw-bold my-1 text-success">{{ metrics.completed_exams_count }}</h3>
            <small class="text-muted">Assessed evaluations</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-info border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Published Scores</span>
            <h3 class="fw-bold my-1 text-info">{{ metrics.total_evaluations_count }}</h3>
            <small class="text-muted">Evaluations with marks</small>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <ul class="nav nav-pills mb-3 gap-2 bg-white p-2 rounded shadow-sm" role="tablist">
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'upcoming' ? 'active' : '']"
          type="button"
          @click="activeTab = 'upcoming'"
        >
          My Upcoming Bookings
          <span v-if="upcomingBookings.length > 0" class="badge bg-warning text-dark ms-1">
            {{ upcomingBookings.length }}
          </span>
          <span v-else class="badge bg-secondary ms-1">0</span>
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'available' ? 'active' : '']"
          type="button"
          @click="activeTab = 'available'"
        >
          Available Exams &amp; Booking
          <span class="badge bg-primary ms-1">{{ availableExams.length }}</span>
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'history' ? 'active' : '']"
          type="button"
          @click="activeTab = 'history'"
        >
          History &amp; Results
          <span class="badge bg-secondary ms-1">{{ results.length }}</span>
        </button>
      </li>
    </ul>

    <!-- ================================================================= -->
    <!-- Tab 1: My Bookings / Upcoming Exams Section                       -->
    <!-- ================================================================= -->
    <div v-show="activeTab === 'upcoming'">
      <div class="card shadow-sm border-0 mb-4">
        <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
          <div>
            <h5 class="mb-0 fw-bold text-dark">Upcoming Scheduled Examinations</h5>
            <small class="text-muted">Your active slot reservations and meeting details</small>
          </div>
          <button class="btn btn-outline-primary btn-sm" @click="activeTab = 'available'">
            + Book Another Examination
          </button>
        </div>
        <div class="card-body p-0">
          <div v-if="upcomingBookings.length === 0" class="text-center py-5">
            <h6 class="text-muted fw-normal">You have no upcoming examination bookings.</h6>
            <button class="btn btn-primary btn-sm mt-2" @click="activeTab = 'available'">
              Explore Available Examinations &rarr;
            </button>
          </div>
          <div v-else class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead class="table-light">
                <tr>
                  <th style="width: 80px;">Booking</th>
                  <th>Course &amp; Examination</th>
                  <th>Scheduled Date &amp; Time</th>
                  <th>Examiner</th>
                  <th>Online Meeting Link</th>
                  <th style="width: 100px;">Status</th>
                  <th style="width: 160px;" class="text-end">Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="b in upcomingBookings" :key="b.booking_id">
                  <td class="text-muted fw-semibold">#{{ b.booking_id }}</td>
                  <td>
                    <div class="fw-bold text-dark">{{ b.examination?.name }}</div>
                    <span class="badge bg-primary me-1">{{ b.course?.code }}</span>
                    <span class="badge bg-info text-dark">{{ b.examination?.type }}</span>
                  </td>
                  <td>
                    <div class="fw-semibold text-dark">{{ b.slot?.date }}</div>
                    <small class="text-muted">{{ b.slot?.start_time }} &ndash; {{ b.slot?.end_time }}</small>
                  </td>
                  <td>
                    <div class="fw-semibold">{{ b.examiner?.name }}</div>
                    <small class="text-muted">{{ b.examiner?.department }}</small>
                  </td>
                  <td>
                    <a
                      v-if="b.slot?.meeting_link"
                      :href="b.slot.meeting_link"
                      target="_blank"
                      rel="noopener"
                      class="btn btn-sm btn-outline-success py-0 px-2 fw-semibold"
                    >
                      Join Exam Call &nearr;
                    </a>
                    <span v-else class="text-muted small">Link to be shared</span>
                  </td>
                  <td>
                    <span class="badge bg-warning text-dark">Booked</span>
                  </td>
                  <td class="text-end">
                    <button
                      v-if="b.can_cancel"
                      class="btn btn-outline-danger btn-sm"
                      :disabled="cancellingBookingId === b.booking_id"
                      @click="confirmCancelBooking(b)"
                    >
                      <span v-if="cancellingBookingId === b.booking_id" class="spinner-border spinner-border-sm me-1"></span>
                      Cancel Slot
                    </button>
                    <span
                      v-else
                      class="badge bg-light text-muted border"
                      title="Cancellation deadline has passed"
                    >
                      Locked (Deadline passed)
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- Tab 2: Available Examinations & Slot Booking                      -->
    <!-- ================================================================= -->
    <div v-show="activeTab === 'available'">
      <div class="card shadow-sm border-0 mb-4">
        <div class="card-header bg-white py-3">
          <div class="row g-2 align-items-center">
            <div class="col-12 col-md-6">
              <h5 class="mb-0 fw-bold text-dark">Examinations Open for Booking</h5>
              <small class="text-muted">Select an examination to browse available evaluation time slots</small>
            </div>
            <div class="col-12 col-md-6">
              <div class="input-group input-group-sm">
                <input
                  v-model.trim="examSearchQuery"
                  type="text"
                  class="form-control"
                  placeholder="Filter by exam name, course code, or type..."
                  @input="handleFilterExams"
                />
                <button
                  v-if="examSearchQuery"
                  class="btn btn-outline-secondary"
                  type="button"
                  @click="clearExamFilter"
                >
                  Clear
                </button>
              </div>
            </div>
          </div>
        </div>

        <div class="card-body p-0">
          <div v-if="filteredExams.length === 0" class="text-center py-5 text-muted">
            No examinations currently open for booking matching your search.
          </div>
          <div v-else class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead class="table-light">
                <tr>
                  <th>Course &amp; Examination</th>
                  <th style="width: 110px;">Type</th>
                  <th>Booking Window Deadline</th>
                  <th style="width: 140px;">Available Slots</th>
                  <th style="width: 140px;">My Status</th>
                  <th style="width: 160px;" class="text-end">Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="ex in filteredExams" :key="ex.id">
                  <td>
                    <div class="fw-bold text-dark">{{ ex.name }}</div>
                    <span class="badge bg-primary me-1">{{ ex.course_code }}</span>
                    <small class="text-muted">{{ ex.course_name }}</small>
                  </td>
                  <td>
                    <span class="badge bg-info text-dark">{{ ex.type }}</span>
                  </td>
                  <td>
                    <div class="small fw-semibold text-danger">
                      Closes: {{ formatDate(ex.slot_booking_end_date) }}
                    </div>
                    <small class="text-muted">Opened: {{ formatDate(ex.slot_booking_start_date) }}</small>
                  </td>
                  <td>
                    <span
                      :class="[
                        'badge',
                        ex.available_slots_count > 0 ? 'bg-success' : 'bg-secondary',
                      ]"
                    >
                      {{ ex.available_slots_count }} slot(s) available
                    </span>
                  </td>
                  <td>
                    <span v-if="ex.has_active_booking" class="badge bg-warning text-dark">
                      &#10003; Already Booked
                    </span>
                    <span v-else class="badge bg-light text-muted border">
                      Not Booked
                    </span>
                  </td>
                  <td class="text-end">
                    <button
                      v-if="ex.has_active_booking"
                      class="btn btn-outline-secondary btn-sm"
                      @click="activeTab = 'upcoming'"
                    >
                      View My Booking
                    </button>
                    <button
                      v-else-if="ex.available_slots_count > 0"
                      class="btn btn-primary btn-sm fw-semibold"
                      @click="openSlotsModal(ex)"
                    >
                      View &amp; Book Slot &rarr;
                    </button>
                    <button
                      v-else
                      class="btn btn-outline-secondary btn-sm"
                      disabled
                    >
                      No Slots Open
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- Tab 3: History & Results Section                                  -->
    <!-- ================================================================= -->
    <div v-show="activeTab === 'history'">
      <!-- Results & Feedback Card -->
      <div class="card shadow-sm border-0 mb-4">
        <div class="card-header bg-white py-3">
          <h5 class="mb-0 fw-bold text-dark">Evaluated Examinations &amp; Scores</h5>
          <small class="text-muted">Examiner grades and qualitative feedback remarks</small>
        </div>
        <div class="card-body p-0">
          <div v-if="results.length === 0" class="text-center py-5 text-muted">
            No examination results published yet. Completed assessments will appear here.
          </div>
          <div v-else class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead class="table-light">
                <tr>
                  <th>Course &amp; Examination</th>
                  <th>Slot Taken</th>
                  <th>Examiner</th>
                  <th style="width: 140px;">Marks Scored</th>
                  <th>Feedback &amp; Remarks</th>
                  <th style="width: 140px;">Evaluation Date</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="res in results" :key="res.booking_id">
                  <td>
                    <div class="fw-bold text-dark">{{ res.examination?.name }}</div>
                    <span class="badge bg-primary me-1">{{ res.course?.code }}</span>
                    <span class="badge bg-info text-dark">{{ res.examination?.type }}</span>
                  </td>
                  <td>
                    <div class="small fw-semibold">{{ res.slot?.date }}</div>
                    <small class="text-muted">{{ res.slot?.start_time }} &ndash; {{ res.slot?.end_time }}</small>
                  </td>
                  <td>
                    <div class="fw-semibold">{{ res.examiner?.name }}</div>
                    <small class="text-muted">{{ res.examiner?.department }}</small>
                  </td>
                  <td>
                    <span class="badge bg-success fs-6 fw-bold">
                      {{ res.evaluation?.total_marks }} marks
                    </span>
                  </td>
                  <td>
                    <div v-if="res.evaluation?.remarks" class="small text-secondary">
                      &ldquo;{{ res.evaluation.remarks }}&rdquo;
                    </div>
                    <span v-else class="text-muted small">No written remarks</span>
                  </td>
                  <td class="small text-muted">
                    {{ formatDate(res.evaluation?.evaluation_date) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Complete Booking History -->
      <div class="card shadow-sm border-0">
        <div class="card-header bg-white py-3">
          <h5 class="mb-0 fw-bold text-dark">Complete Booking Activity Log</h5>
          <small class="text-muted">History of all reservations, completions, and cancellations</small>
        </div>
        <div class="table-responsive">
          <table class="table table-sm table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 80px;">Booking</th>
                <th>Examination</th>
                <th>Slot Date &amp; Time</th>
                <th>Reserved On</th>
                <th style="width: 120px;">Final Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="bookingHistory.length === 0">
                <td colspan="5" class="text-center text-muted py-3">No booking history logged.</td>
              </tr>
              <tr v-for="bh in bookingHistory" :key="bh.booking_id">
                <td class="text-muted fw-semibold">#{{ bh.booking_id }}</td>
                <td>
                  <strong>{{ bh.examination?.name }}</strong> ({{ bh.course?.code }})
                </td>
                <td>{{ bh.slot?.date }} {{ bh.slot?.start_time }}</td>
                <td class="small text-muted">{{ formatDate(bh.booking_date) }}</td>
                <td>
                  <span
                    :class="[
                      'badge',
                      bh.status === 'Completed' ? 'bg-success' : '',
                      bh.status === 'Booked' ? 'bg-warning text-dark' : '',
                      bh.status === 'Cancelled' ? 'bg-danger' : '',
                    ]"
                  >
                    {{ bh.status }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- MODAL: View Available Slots & Book                                -->
    <!-- ================================================================= -->
    <div
      v-if="showSlotsModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog modal-lg">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-primary text-white">
            <h5 class="modal-title">
              Available Slots: {{ selectedExamForSlots?.name }}
            </h5>
            <button type="button" class="btn-close btn-close-white" @click="showSlotsModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="p-3 bg-light border rounded mb-3 small">
              <div class="row g-2">
                <div class="col-sm-6">
                  <div><strong>Course:</strong> {{ selectedExamForSlots?.course_code }} - {{ selectedExamForSlots?.course_name }}</div>
                  <div><strong>Type:</strong> {{ selectedExamForSlots?.type }}</div>
                </div>
                <div class="col-sm-6 text-sm-end">
                  <div><strong>Booking Deadline:</strong> {{ formatDate(selectedExamForSlots?.slot_booking_end_date) }}</div>
                  <div class="text-muted">A student may only reserve 1 slot per examination.</div>
                </div>
              </div>
            </div>

            <!-- Error banner inside modal if booking conflict -->
            <div v-if="modalErrorMessage" class="alert alert-danger py-2 small mb-3">
              {{ modalErrorMessage }}
            </div>

            <div v-if="loadingSlots" class="text-center py-4">
              <div class="spinner-border text-primary" role="status"></div>
              <div class="small text-muted mt-2">Loading available slots...</div>
            </div>

            <div v-else-if="availableSlotsList.length === 0" class="text-center py-4 text-muted">
              No available slots remaining for this examination.
            </div>

            <div v-else class="table-responsive">
              <table class="table table-hover align-middle">
                <thead class="table-light">
                  <tr>
                    <th>Date</th>
                    <th>Time Window</th>
                    <th>Examiner</th>
                    <th class="text-center" style="width: 140px;">Seats Remaining</th>
                    <th class="text-end" style="width: 130px;">Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="slot in availableSlotsList" :key="slot.id">
                    <td class="fw-bold">{{ slot.date }}</td>
                    <td>{{ slot.start_time }} &ndash; {{ slot.end_time }}</td>
                    <td>
                      <div class="fw-semibold">{{ slot.examiner_name }}</div>
                      <small class="text-muted">{{ slot.examiner_department }}</small>
                    </td>
                    <td class="text-center">
                      <span class="badge bg-success fs-6">
                        {{ slot.available_seats }} / {{ slot.max_capacity }} left
                      </span>
                    </td>
                    <td class="text-end">
                      <button
                        class="btn btn-primary btn-sm fw-semibold"
                        :disabled="bookingSlotId === slot.id || slot.available_seats <= 0"
                        @click="handleBookSlot(slot)"
                      >
                        <span v-if="bookingSlotId === slot.id" class="spinner-border spinner-border-sm me-1"></span>
                        Book Slot
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer bg-light">
            <button type="button" class="btn btn-secondary btn-sm" @click="showSlotsModal = false">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";
import apiClient from "../services/api";

const router = useRouter();
const authStore = useAuthStore();

// UI State
const loading = ref(false);
const activeTab = ref("upcoming");
const bookingSlotId = ref(null);
const cancellingBookingId = ref(null);

// Alerts
const alertMessage = ref({ type: "success", text: "" });
function showAlert(text, type = "success") {
  alertMessage.value = { type, text };
  if (type === "success") {
    setTimeout(() => {
      if (alertMessage.value.text === text) {
        clearAlert();
      }
    }, 5000);
  }
}
function clearAlert() {
  alertMessage.value = { type: "success", text: "" };
}

// Data
const metrics = ref({
  active_bookings_count: 0,
  completed_exams_count: 0,
  available_exams_count: 0,
  total_evaluations_count: 0,
});
const availableExams = ref([]);
const upcomingBookings = ref([]);
const bookingHistory = ref([]);
const results = ref([]);

// Examination Filter Search
const examSearchQuery = ref("");
const filteredExams = computed(() => {
  if (!examSearchQuery.value) return availableExams.value;
  const q = examSearchQuery.value.toLowerCase();
  return availableExams.value.filter(
    (ex) =>
      ex.name?.toLowerCase().includes(q) ||
      ex.course_code?.toLowerCase().includes(q) ||
      ex.type?.toLowerCase().includes(q)
  );
});

// Slots Modal State
const showSlotsModal = ref(false);
const selectedExamForSlots = ref(null);
const availableSlotsList = ref([]);
const loadingSlots = ref(false);
const modalErrorMessage = ref("");

// ---------------------------------------------------------------------------
// API Data Fetchers
// ---------------------------------------------------------------------------

async function fetchDashboard() {
  try {
    const res = await apiClient.get("/api/student/dashboard");
    metrics.value = res.data.metrics || metrics.value;
    availableExams.value = res.data.open_examinations || [];
    upcomingBookings.value = res.data.upcoming_bookings || [];
    bookingHistory.value = res.data.booking_history || [];
    results.value = res.data.results || [];
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to load dashboard data.", "danger");
  }
}

async function refreshAllData() {
  loading.value = true;
  clearAlert();
  try {
    await fetchDashboard();
  } finally {
    loading.value = false;
  }
}

function handleFilterExams() {
  // Handled via computed property filteredExams
}

function clearExamFilter() {
  examSearchQuery.value = "";
}

// ---------------------------------------------------------------------------
// Slot Browsing & Booking
// ---------------------------------------------------------------------------

async function openSlotsModal(exam) {
  selectedExamForSlots.value = exam;
  modalErrorMessage.value = "";
  loadingSlots.value = true;
  showSlotsModal.value = true;
  try {
    const res = await apiClient.get(`/api/student/examinations/${exam.id}/slots`);
    availableSlotsList.value = res.data.slots || [];
  } catch (err) {
    modalErrorMessage.value = err.response?.data?.message || "Failed to fetch slots.";
  } finally {
    loadingSlots.value = false;
  }
}

async function handleBookSlot(slot) {
  modalErrorMessage.value = "";
  bookingSlotId.value = slot.id;
  try {
    const res = await apiClient.post("/api/student/bookings", {
      slot_id: slot.id,
    });
    showAlert(res.data.message || "Examination slot reserved successfully!");
    showSlotsModal.value = false;
    await fetchDashboard();
    activeTab.value = "upcoming";
  } catch (err) {
    const errorMsg =
      err.response?.data?.message ||
      "Unable to book slot. It might be full or you may already have a booking.";
    modalErrorMessage.value = errorMsg;
    showAlert(errorMsg, "danger");
  } finally {
    bookingSlotId.value = null;
  }
}

// ---------------------------------------------------------------------------
// Cancel Booking
// ---------------------------------------------------------------------------

async function confirmCancelBooking(booking) {
  const confirmMsg = `Are you sure you want to cancel your slot reservation for "${booking.examination?.name}" on ${booking.slot?.date}? Your reserved seat will be released.`;
  if (!confirm(confirmMsg)) return;

  cancellingBookingId.value = booking.booking_id;
  try {
    const res = await apiClient.post(
      `/api/student/bookings/${booking.booking_id}/cancel`
    );
    showAlert(res.data.message || "Booking cancelled successfully.");
    await fetchDashboard();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to cancel booking.", "danger");
  } finally {
    cancellingBookingId.value = null;
  }
}

// ---------------------------------------------------------------------------
// Helpers & Lifecycle
// ---------------------------------------------------------------------------

function formatDate(dtStr) {
  if (!dtStr) return "-";
  try {
    const d = new Date(dtStr);
    return d.toLocaleString([], {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return dtStr;
  }
}

function handleLogout() {
  authStore.logout();
  router.push("/login");
}

onMounted(() => {
  refreshAllData();
});
</script>

<style scoped>
.table th {
  font-weight: 600;
  font-size: 0.85rem;
  letter-spacing: 0.02em;
}
.table td {
  font-size: 0.9rem;
}
</style>
