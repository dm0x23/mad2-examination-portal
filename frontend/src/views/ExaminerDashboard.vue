<template>
  <div class="container-fluid py-4 px-md-4">
    <!-- Header -->
    <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
      <div>
        <h2 class="h3 fw-bold mb-1 text-dark">Examiner Portal</h2>
        <p class="text-muted mb-0 small">
          Examination Management Portal V2 &bull; Logged in as
          <span class="fw-semibold text-primary">{{ examinerDisplayName }}</span>
          <span class="badge bg-warning text-dark ms-2">Examiner</span>
          <span v-if="examinerDepartment" class="badge bg-secondary ms-1">{{ examinerDepartment }}</span>
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

    <!-- Summary Statistics Bar -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-primary border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Assigned Exams</span>
            <h3 class="fw-bold my-1 text-primary">{{ metrics.assigned_examinations_count }}</h3>
            <small class="text-muted">Eligible for slots</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-info border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">My Slots Created</span>
            <h3 class="fw-bold my-1 text-info">{{ metrics.total_slots }}</h3>
            <small class="text-muted">Across all timelines</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-warning border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Booked Students</span>
            <h3 class="fw-bold my-1 text-warning">{{ metrics.booked_students }}</h3>
            <small class="text-muted">Enrolled in my slots</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-3">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-danger border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Pending Evaluations</span>
            <h3 class="fw-bold my-1 text-danger">{{ metrics.pending_evaluations }}</h3>
            <small class="text-muted">Awaiting scoring</small>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <ul class="nav nav-pills mb-3 gap-2 bg-white p-2 rounded shadow-sm" role="tablist">
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'slots' ? 'active' : '']"
          type="button"
          @click="activeTab = 'slots'"
        >
          My Examination Slots
          <span class="badge bg-secondary ms-1">{{ slots.length }}</span>
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'evaluations' ? 'active' : '']"
          type="button"
          @click="activeTab = 'evaluations'"
        >
          Student Bookings &amp; Evaluations
          <span v-if="metrics.pending_evaluations > 0" class="badge bg-danger ms-1">
            {{ metrics.pending_evaluations }} Pending
          </span>
          <span v-else class="badge bg-secondary ms-1">{{ bookings.length }}</span>
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'examinations' ? 'active' : '']"
          type="button"
          @click="activeTab = 'examinations'"
        >
          Active Examinations Overview
        </button>
      </li>
    </ul>

    <!-- ================================================================= -->
    <!-- Tab 1: My Examination Slots Section                               -->
    <!-- ================================================================= -->
    <div v-show="activeTab === 'slots'">
      <div class="card shadow-sm border-0 mb-4">
        <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
          <div>
            <h5 class="mb-0 fw-bold text-dark">My Created Examination Slots</h5>
            <small class="text-muted">Manage your available evaluation schedules and links</small>
          </div>
          <button class="btn btn-primary btn-sm fw-semibold" @click="openCreateSlotModal">
            + Create New Slot
          </button>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 80px;">Slot ID</th>
                <th>Examination / Course</th>
                <th>Date &amp; Time</th>
                <th>Capacity &amp; Bookings</th>
                <th>Meeting Link</th>
                <th style="width: 110px;">Status</th>
                <th style="width: 150px;" class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="slots.length === 0">
                <td colspan="7" class="text-center text-muted py-4">
                  You haven't created any examination slots yet. Click "+ Create New Slot" to add one.
                </td>
              </tr>
              <tr v-for="s in slots" :key="s.id">
                <td class="text-muted fw-semibold">#{{ s.id }}</td>
                <td>
                  <div class="fw-bold text-dark">{{ s.examination_name }}</div>
                  <span class="badge bg-primary me-1">{{ s.course_code }}</span>
                  <small class="text-muted">{{ s.course_name }}</small>
                </td>
                <td>
                  <div class="fw-semibold">{{ s.date }}</div>
                  <small class="text-muted">{{ s.start_time }} &ndash; {{ s.end_time }}</small>
                </td>
                <td>
                  <span class="badge bg-light text-dark border">
                    {{ s.available_seats }} of {{ s.max_capacity }} available
                  </span>
                  <div class="small mt-1">
                    <span :class="s.bookings_count > 0 ? 'text-primary fw-semibold' : 'text-muted'">
                      {{ s.bookings_count }} student(s) booked
                    </span>
                  </div>
                </td>
                <td>
                  <a
                    v-if="s.meeting_link"
                    :href="s.meeting_link"
                    target="_blank"
                    rel="noopener"
                    class="btn btn-sm btn-outline-info text-truncate py-0 px-2"
                    style="max-width: 180px;"
                  >
                    Open Meeting &nearr;
                  </a>
                  <span v-else class="text-muted small">None</span>
                </td>
                <td>
                  <span
                    :class="[
                      'badge',
                      s.status === 'Available' ? 'bg-success' : '',
                      s.status === 'Full' ? 'bg-warning text-dark' : '',
                      s.status === 'Cancelled' ? 'bg-danger' : '',
                      s.status === 'Completed' ? 'bg-secondary' : '',
                    ]"
                  >
                    {{ s.status }}
                  </span>
                </td>
                <td class="text-end">
                  <div v-if="s.bookings_count > 0">
                    <span
                      class="badge bg-light text-muted border"
                      title="Editing and deletion disabled because students have already booked this slot"
                    >
                      Booked (Locked)
                    </span>
                  </div>
                  <div v-else class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary" @click="openEditSlotModal(s)">
                      Edit
                    </button>
                    <button class="btn btn-outline-danger" @click="confirmDeleteSlot(s)">
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- Tab 2: Student Bookings & Evaluations Section                     -->
    <!-- ================================================================= -->
    <div v-show="activeTab === 'evaluations'">
      <div class="card shadow-sm border-0">
        <div class="card-header bg-white py-3 d-flex flex-wrap justify-content-between align-items-center gap-2">
          <div>
            <h5 class="mb-0 fw-bold text-dark">Booked Students &amp; Assessment</h5>
            <small class="text-muted">Grade candidate submissions according to predefined rubric criteria</small>
          </div>
          <div class="d-flex gap-2">
            <select v-model="bookingFilterStatus" class="form-select form-select-sm" style="width: 170px;">
              <option value="all">All Bookings</option>
              <option value="pending">Awaiting Evaluation</option>
              <option value="completed">Completed</option>
            </select>
            <button class="btn btn-outline-secondary btn-sm" @click="fetchBookings">
              &#x21bb; Reload
            </button>
          </div>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 70px;">ID</th>
                <th>Candidate / Student</th>
                <th>Examination</th>
                <th>Slot Time</th>
                <th>Meeting Link</th>
                <th style="width: 120px;">Status</th>
                <th>Evaluation / Marks</th>
                <th style="width: 140px;" class="text-end">Assessment</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="filteredBookings.length === 0">
                <td colspan="8" class="text-center text-muted py-4">
                  No student bookings match the selected criteria.
                </td>
              </tr>
              <tr v-for="b in filteredBookings" :key="b.booking_id">
                <td class="text-muted fw-semibold">#{{ b.booking_id }}</td>
                <td>
                  <div class="fw-bold">{{ b.student_name }}</div>
                  <small class="text-muted">{{ b.student_email }} (Student #{{ b.student_id }})</small>
                </td>
                <td>
                  <div class="fw-semibold">{{ b.examination_name }}</div>
                  <span class="badge bg-primary">{{ b.course_code }}</span>
                  <span class="badge bg-info text-dark ms-1">{{ b.examination_type }}</span>
                </td>
                <td>
                  <div class="small fw-semibold">{{ b.slot_date }}</div>
                  <small class="text-muted">{{ b.slot_start_time }} &ndash; {{ b.slot_end_time }}</small>
                </td>
                <td>
                  <a
                    v-if="b.meeting_link"
                    :href="b.meeting_link"
                    target="_blank"
                    rel="noopener"
                    class="btn btn-sm btn-outline-primary py-0 px-2"
                  >
                    Join Call &nearr;
                  </a>
                  <span v-else class="text-muted small">-</span>
                </td>
                <td>
                  <span
                    :class="[
                      'badge',
                      b.status === 'Completed' ? 'bg-success' : 'bg-warning text-dark',
                    ]"
                  >
                    {{ b.status === 'Completed' ? 'Evaluated' : 'Pending' }}
                  </span>
                </td>
                <td>
                  <div v-if="b.has_evaluation">
                    <span class="badge bg-success fs-6">{{ b.evaluation.total_marks }} marks</span>
                    <div v-if="b.evaluation.remarks" class="small text-muted text-truncate mt-1" style="max-width: 200px;">
                      "{{ b.evaluation.remarks }}"
                    </div>
                  </div>
                  <span v-else class="text-muted small">Not yet evaluated</span>
                </td>
                <td class="text-end">
                  <button
                    v-if="b.status === 'Completed' || b.has_evaluation"
                    class="btn btn-sm btn-outline-success fw-semibold"
                    @click="openReviewScorecardModal(b)"
                  >
                    View Scorecard &rarr;
                  </button>
                  <button
                    v-else
                    class="btn btn-sm btn-primary fw-semibold"
                    @click="openEvaluationModal(b)"
                  >
                    Grade Candidate &rarr;
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- Tab 3: Active Examinations Overview                               -->
    <!-- ================================================================= -->
    <div v-show="activeTab === 'examinations'">
      <div class="card shadow-sm border-0">
        <div class="card-header bg-white py-3">
          <h5 class="mb-0 fw-bold text-dark">Active Examinations &amp; Timelines</h5>
          <small class="text-muted">Review current timeline windows for slot creation and student bookings</small>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th>Course &amp; Examination</th>
                <th>Type</th>
                <th>Slot Creation Window</th>
                <th>Student Booking Window</th>
                <th>Slot Creation Status</th>
                <th>My Slots</th>
                <th>Rubric Criteria</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="examinations.length === 0">
                <td colspan="7" class="text-center text-muted py-4">No active examinations found.</td>
              </tr>
              <tr v-for="ex in examinations" :key="ex.id">
                <td>
                  <div class="fw-bold">{{ ex.name }}</div>
                  <span class="badge bg-primary">{{ ex.course_code }}</span>
                  <small class="text-muted ms-1">{{ ex.course_name }}</small>
                </td>
                <td><span class="badge bg-info text-dark">{{ ex.type }}</span></td>
                <td class="small text-muted">
                  <div><strong>Start:</strong> {{ formatDate(ex.slot_creation_start_date) }}</div>
                  <div><strong>End:</strong> {{ formatDate(ex.slot_creation_end_date) }}</div>
                </td>
                <td class="small text-muted">
                  <div><strong>Start:</strong> {{ formatDate(ex.slot_booking_start_date) }}</div>
                  <div><strong>End:</strong> {{ formatDate(ex.slot_booking_end_date) }}</div>
                </td>
                <td>
                  <span
                    :class="[
                      'badge',
                      ex.slot_creation_open ? 'bg-success' : 'bg-secondary',
                    ]"
                  >
                    {{ ex.slot_creation_open ? 'Open for Slot Creation' : 'Creation Closed' }}
                  </span>
                </td>
                <td>
                  <span class="badge bg-light text-dark border">{{ ex.my_slots_count }} slot(s)</span>
                </td>
                <td>
                  <div v-if="ex.rubrics && ex.rubrics.length > 0" class="small">
                    <strong>{{ ex.rubrics.length }} criteria</strong> (Max: {{ ex.total_rubric_max_marks || 0 }})
                  </div>
                  <span v-else class="text-muted small">No rubrics</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- MODAL 1: Create New Slot Modal                                    -->
    <!-- ================================================================= -->
    <div
      v-if="showCreateSlotModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-primary text-white">
            <h5 class="modal-title">Create Examination Slot</h5>
            <button type="button" class="btn-close btn-close-white" @click="showCreateSlotModal = false"></button>
          </div>
          <form @submit.prevent="handleCreateSlot">
            <div class="modal-body">
              <!-- Select Examination -->
              <div class="mb-3">
                <label class="form-label fw-semibold">Target Examination <span class="text-danger">*</span></label>
                <select
                  v-model="slotForm.examination_id"
                  class="form-select"
                  required
                >
                  <option value="" disabled>-- Select Examination --</option>
                  <option
                    v-for="ex in examinations"
                    :key="ex.id"
                    :value="ex.id"
                  >
                    {{ ex.course_code }} - {{ ex.name }} ({{ ex.slot_creation_open ? 'Open' : 'Closed' }})
                  </option>
                </select>
              </div>

              <!-- Window Status Check Alert -->
              <div
                v-if="selectedExamForSlot && !selectedExamForSlot.slot_creation_open"
                class="alert alert-warning py-2 small mb-3"
              >
                <strong>Notice:</strong> Slot creation is currently closed for this examination based on the defined timeline window ({{ formatDate(selectedExamForSlot.slot_creation_start_date) }} &ndash; {{ formatDate(selectedExamForSlot.slot_creation_end_date) }}).
              </div>

              <!-- Date -->
              <div class="mb-3">
                <label class="form-label fw-semibold">Date <span class="text-danger">*</span></label>
                <input
                  v-model="slotForm.date"
                  type="date"
                  class="form-control"
                  required
                />
              </div>

              <!-- Times -->
              <div class="row g-2 mb-3">
                <div class="col-6">
                  <label class="form-label fw-semibold">Start Time <span class="text-danger">*</span></label>
                  <input
                    v-model="slotForm.start_time"
                    type="time"
                    class="form-control"
                    required
                  />
                </div>
                <div class="col-6">
                  <label class="form-label fw-semibold">End Time <span class="text-danger">*</span></label>
                  <input
                    v-model="slotForm.end_time"
                    type="time"
                    class="form-control"
                    required
                  />
                </div>
              </div>

              <!-- Capacity -->
              <div class="mb-3">
                <label class="form-label fw-semibold">Max Student Capacity <span class="text-danger">*</span></label>
                <input
                  v-model.number="slotForm.max_capacity"
                  type="number"
                  min="1"
                  max="50"
                  class="form-control"
                  placeholder="1"
                  required
                />
                <small class="text-muted">Available seats will be set equal to max capacity.</small>
              </div>

              <!-- Meeting Link -->
              <div class="mb-3">
                <label class="form-label fw-semibold">Online Meeting Link</label>
                <input
                  v-model.trim="slotForm.meeting_link"
                  type="url"
                  class="form-control"
                  placeholder="https://meet.google.com/xyz-exam"
                />
              </div>
            </div>
            <div class="modal-footer bg-light">
              <button type="button" class="btn btn-secondary" @click="showCreateSlotModal = false">
                Cancel
              </button>
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="formSubmitting || (selectedExamForSlot && !selectedExamForSlot.slot_creation_open)"
              >
                {{ formSubmitting ? 'Creating Slot...' : 'Create Slot' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- MODAL 2: Edit Slot Modal                                          -->
    <!-- ================================================================= -->
    <div
      v-if="showEditSlotModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-dark text-white">
            <h5 class="modal-title">Edit Slot #{{ editingSlot?.id }}</h5>
            <button type="button" class="btn-close btn-close-white" @click="showEditSlotModal = false"></button>
          </div>
          <form @submit.prevent="handleUpdateSlot">
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label small fw-semibold">Examination</label>
                <div class="p-2 border rounded bg-light small">
                  <strong>{{ editingSlot?.examination_name }}</strong> ({{ editingSlot?.course_code }})
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">Date <span class="text-danger">*</span></label>
                <input
                  v-model="editSlotForm.date"
                  type="date"
                  class="form-control"
                  required
                />
              </div>

              <div class="row g-2 mb-3">
                <div class="col-6">
                  <label class="form-label fw-semibold">Start Time <span class="text-danger">*</span></label>
                  <input
                    v-model="editSlotForm.start_time"
                    type="time"
                    class="form-control"
                    required
                  />
                </div>
                <div class="col-6">
                  <label class="form-label fw-semibold">End Time <span class="text-danger">*</span></label>
                  <input
                    v-model="editSlotForm.end_time"
                    type="time"
                    class="form-control"
                    required
                  />
                </div>
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">Max Student Capacity <span class="text-danger">*</span></label>
                <input
                  v-model.number="editSlotForm.max_capacity"
                  type="number"
                  min="1"
                  max="50"
                  class="form-control"
                  required
                />
              </div>

              <div class="mb-3">
                <label class="form-label fw-semibold">Meeting Link</label>
                <input
                  v-model.trim="editSlotForm.meeting_link"
                  type="url"
                  class="form-control"
                />
              </div>
            </div>
            <div class="modal-footer bg-light">
              <button type="button" class="btn btn-secondary" @click="showEditSlotModal = false">
                Cancel
              </button>
              <button type="submit" class="btn btn-dark" :disabled="formSubmitting">
                {{ formSubmitting ? 'Saving...' : 'Update Slot' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- MODAL 3: Student Evaluation & Grading Modal                       -->
    <!-- ================================================================= -->
    <div
      v-if="showEvaluationModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog modal-lg">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-success text-white">
            <h5 class="modal-title">
              Student Assessment &amp; Grading
            </h5>
            <button type="button" class="btn-close btn-close-white" @click="showEvaluationModal = false"></button>
          </div>
          <form @submit.prevent="handleSaveEvaluation">
            <div class="modal-body">
              <!-- Student & Exam Details -->
              <div class="row g-2 mb-3 p-3 bg-light border rounded small">
                <div class="col-md-6">
                  <div><strong>Student Candidate:</strong> {{ selectedBooking?.student_name }}</div>
                  <div><strong>Email:</strong> {{ selectedBooking?.student_email }}</div>
                </div>
                <div class="col-md-6">
                  <div><strong>Examination:</strong> {{ selectedBooking?.examination_name }} ({{ selectedBooking?.course_code }})</div>
                  <div><strong>Slot:</strong> {{ selectedBooking?.slot_date }} ({{ selectedBooking?.slot_start_time }} &ndash; {{ selectedBooking?.slot_end_time }})</div>
                </div>
              </div>

              <!-- Predefined Rubrics Table -->
              <div class="mb-3">
                <h6 class="fw-bold text-secondary mb-2">Examination Rubric Criteria</h6>
                <div v-if="selectedBooking?.rubrics && selectedBooking.rubrics.length > 0" class="table-responsive">
                  <table class="table table-sm table-bordered align-middle">
                    <thead class="table-light">
                      <tr>
                        <th>Criterion</th>
                        <th style="width: 120px;" class="text-center">Max Marks</th>
                        <th style="width: 120px;" class="text-center">Weightage</th>
                        <th style="width: 140px;" class="text-center">Marks Given</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="rubric in selectedBooking.rubrics" :key="rubric.id">
                        <td>{{ rubric.criterion_name }}</td>
                        <td class="text-center">{{ rubric.max_marks }}</td>
                        <td class="text-center">{{ rubric.weightage }}%</td>
                        <td>
                          <input
                            v-model.number="rubricScores[rubric.id]"
                            type="number"
                            step="0.5"
                            min="0"
                            :max="rubric.max_marks"
                            class="form-control form-control-sm text-center"
                            placeholder="0"
                            @input="updateTotalMarksFromRubrics"
                          />
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <div v-else class="text-muted small p-2 border rounded bg-white">
                  No predefined rubrics configured for this exam. You can directly score the candidate below.
                </div>
              </div>

              <!-- Total Marks Input -->
              <div class="row g-3 mb-3 align-items-center">
                <div class="col-md-6">
                  <label class="form-label fw-bold">
                    Total Marks Obtained <span class="text-danger">*</span>
                    <span v-if="rubricsTotalAllowedMarks > 0" class="badge bg-secondary ms-1">
                      Max: {{ rubricsTotalAllowedMarks }}
                    </span>
                  </label>
                  <input
                    v-model.number="evaluationForm.marks_obtained"
                    type="number"
                    step="0.5"
                    min="0"
                    :max="rubricsTotalAllowedMarks > 0 ? rubricsTotalAllowedMarks : 100"
                    class="form-control form-control-lg fw-bold text-success"
                    placeholder="Enter total marks"
                    required
                  />
                  <div
                    v-if="rubricsTotalAllowedMarks > 0 && evaluationForm.marks_obtained > rubricsTotalAllowedMarks"
                    class="text-danger small mt-1"
                  >
                    Entered marks exceed maximum permitted marks ({{ rubricsTotalAllowedMarks }}).
                  </div>
                </div>
              </div>

              <!-- Remarks -->
              <div class="mb-3">
                <label class="form-label fw-semibold">Examiner Remarks &amp; Feedback</label>
                <textarea
                  v-model.trim="evaluationForm.remarks"
                  class="form-control"
                  rows="3"
                  placeholder="Provide structured feedback, candidate strengths, and areas for improvement..."
                ></textarea>
              </div>
            </div>
            <div class="modal-footer bg-light">
              <button type="button" class="btn btn-secondary" @click="showEvaluationModal = false">
                Cancel
              </button>
              <button
                type="submit"
                class="btn btn-success fw-semibold"
                :disabled="
                  formSubmitting ||
                  evaluationForm.marks_obtained === null ||
                  evaluationForm.marks_obtained === '' ||
                  (rubricsTotalAllowedMarks > 0 && evaluationForm.marks_obtained > rubricsTotalAllowedMarks)
                "
              >
                {{ formSubmitting ? 'Submitting Grading...' : 'Submit Evaluation' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- MODAL 4: Read-Only Review Graded Scorecard Modal (Milestone 6)     -->
    <!-- ================================================================= -->
    <div
      v-if="showReviewModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog modal-lg">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-dark text-white">
            <h5 class="modal-title">
              Candidate Evaluation Scorecard &amp; Rubric Feedback (Read-Only)
            </h5>
            <button type="button" class="btn-close btn-close-white" @click="showReviewModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="p-3 bg-light border rounded mb-3">
              <div class="row g-2 align-items-center">
                <div class="col-sm-8">
                  <h5 class="fw-bold text-dark mb-1">
                    {{ selectedReviewBooking?.student_name }}
                  </h5>
                  <div class="text-muted small">
                    Candidate Email: <strong>{{ selectedReviewBooking?.student_email }}</strong> &bull;
                    Student ID: #{{ selectedReviewBooking?.student_id }}
                  </div>
                  <div class="small mt-1 text-muted">
                    Exam: <strong>{{ selectedReviewBooking?.examination_name }}</strong> ({{ selectedReviewBooking?.course_code }})
                  </div>
                </div>
                <div class="col-sm-4 text-sm-end">
                  <div class="text-muted small">Final Total Marks</div>
                  <h2 class="fw-bold text-success mb-0">
                    {{ selectedReviewBooking?.evaluation?.total_marks }}
                    <small class="fs-6 text-muted" v-if="reviewRubricsTotalMaxMarks > 0">/ {{ reviewRubricsTotalMaxMarks }}</small>
                  </h2>
                  <small class="text-muted">
                    Evaluated on: {{ formatDate(selectedReviewBooking?.evaluation?.evaluation_date) }}
                  </small>
                </div>
              </div>
            </div>

            <!-- Rubric Breakdown -->
            <div class="mb-4">
              <h6 class="fw-bold text-secondary mb-2">Evaluated Rubric Criteria Breakdown</h6>
              <div v-if="reviewRubricBreakdownItems.length > 0" class="table-responsive">
                <table class="table table-bordered table-sm align-middle mb-0">
                  <thead class="table-light">
                    <tr>
                      <th>Criterion</th>
                      <th style="width: 120px;" class="text-center">Max Marks</th>
                      <th style="width: 120px;" class="text-center">Weightage</th>
                      <th style="width: 130px;" class="text-center">Score Awarded</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(item, idx) in reviewRubricBreakdownItems" :key="idx">
                      <td class="fw-semibold">{{ item.criterion_name }}</td>
                      <td class="text-center">{{ item.max_marks }}</td>
                      <td class="text-center">{{ item.weightage ? item.weightage + '%' : '-' }}</td>
                      <td class="text-center fw-bold text-success">
                        {{ item.marks !== undefined ? item.marks : '-' }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="p-3 border rounded text-muted small bg-white text-center">
                Graded directly as overall score.
              </div>
            </div>

            <!-- Remarks -->
            <div class="card bg-light border-0">
              <div class="card-body p-3">
                <h6 class="fw-bold text-dark mb-1">Your Submitted Feedback Remarks:</h6>
                <p class="mb-0 text-secondary fst-italic" v-if="selectedReviewBooking?.evaluation?.remarks">
                  &ldquo;{{ selectedReviewBooking?.evaluation?.remarks }}&rdquo;
                </p>
                <p class="mb-0 text-muted small" v-else>
                  No written feedback comments recorded.
                </p>
              </div>
            </div>
          </div>
          <div class="modal-footer bg-light">
            <button type="button" class="btn btn-secondary btn-sm" @click="showReviewModal = false">
              Close Review
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

// General UI State
const loading = ref(false);
const formSubmitting = ref(false);
const activeTab = ref("slots");
const bookingFilterStatus = ref("all");

// Alert banner
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

// Metrics & Data
const metrics = ref({
  assigned_examinations_count: 0,
  total_slots: 0,
  booked_students: 0,
  pending_evaluations: 0,
  completed_evaluations: 0,
});
const examinerInfo = ref(null);
const examinations = ref([]);
const slots = ref([]);
const bookings = ref([]);

const examinerDisplayName = computed(() => {
  return (
    examinerInfo.value?.examiner_profile?.name ||
    examinerInfo.value?.email ||
    authStore.user?.email
  );
});

const examinerDepartment = computed(() => {
  return examinerInfo.value?.examiner_profile?.department || "";
});

const filteredBookings = computed(() => {
  if (bookingFilterStatus.value === "pending") {
    return bookings.value.filter((b) => b.status !== "Completed" && !b.has_evaluation);
  }
  if (bookingFilterStatus.value === "completed") {
    return bookings.value.filter((b) => b.status === "Completed" || b.has_evaluation);
  }
  return bookings.value;
});

// Modals State
const showCreateSlotModal = ref(false);
const slotForm = ref({
  examination_id: "",
  date: "",
  start_time: "",
  end_time: "",
  max_capacity: 1,
  meeting_link: "",
});

const selectedExamForSlot = computed(() => {
  if (!slotForm.value.examination_id) return null;
  return examinations.value.find((e) => e.id === Number(slotForm.value.examination_id)) || null;
});

const showEditSlotModal = ref(false);
const editingSlot = ref(null);
const editSlotForm = ref({
  date: "",
  start_time: "",
  end_time: "",
  max_capacity: 1,
  meeting_link: "",
});

const showEvaluationModal = ref(false);
const selectedBooking = ref(null);
const rubricScores = ref({});
const evaluationForm = ref({
  marks_obtained: null,
  remarks: "",
});

// Review Scorecard Modal (Milestone 6)
const showReviewModal = ref(false);
const selectedReviewBooking = ref(null);

const reviewRubricBreakdownItems = computed(() => {
  if (!selectedReviewBooking.value) return [];
  const evalRec = selectedReviewBooking.value.evaluation;
  if (!evalRec) return [];

  const rawBreakdown = evalRec.rubric_breakdown;
  if (Array.isArray(rawBreakdown) && rawBreakdown.length > 0) {
    return rawBreakdown;
  }

  const examRubrics = selectedReviewBooking.value.rubrics || [];
  if (examRubrics.length > 0) {
    return examRubrics.map((r) => ({
      criterion_name: r.criterion_name,
      max_marks: r.max_marks,
      weightage: r.weightage,
      marks:
        rawBreakdown && typeof rawBreakdown === "object"
          ? rawBreakdown[r.id]
          : undefined,
    }));
  }

  return [];
});

const reviewRubricsTotalMaxMarks = computed(() => {
  if (reviewRubricBreakdownItems.value.length > 0) {
    return reviewRubricBreakdownItems.value.reduce((acc, i) => acc + (i.max_marks || 0), 0);
  }
  const examRubrics = selectedReviewBooking.value?.rubrics || [];
  return examRubrics.reduce((acc, r) => acc + (r.max_marks || 0), 0);
});

function openReviewScorecardModal(booking) {
  selectedReviewBooking.value = booking;
  showReviewModal.value = true;
}

const rubricsTotalAllowedMarks = computed(() => {
  if (!selectedBooking.value?.rubrics || selectedBooking.value.rubrics.length === 0) return 0;
  return selectedBooking.value.rubrics.reduce((acc, r) => acc + (r.max_marks || 0), 0);
});

function updateTotalMarksFromRubrics() {
  if (!selectedBooking.value?.rubrics || selectedBooking.value.rubrics.length === 0) return;
  let total = 0;
  let enteredAny = false;
  for (const r of selectedBooking.value.rubrics) {
    const val = rubricScores.value[r.id];
    if (val !== undefined && val !== null && val !== "") {
      total += Number(val);
      enteredAny = true;
    }
  }
  if (enteredAny) {
    evaluationForm.value.marks_obtained = total;
  }
}

// ---------------------------------------------------------------------------
// API Data Loaders
// ---------------------------------------------------------------------------

async function fetchDashboard() {
  try {
    const res = await apiClient.get("/api/examiner/dashboard");
    metrics.value = res.data.metrics;
    examinerInfo.value = res.data.examiner;
  } catch (err) {
    console.error("Dashboard metrics failed:", err);
  }
}

async function fetchExaminations() {
  try {
    const res = await apiClient.get("/api/examiner/examinations");
    examinations.value = res.data.examinations || [];
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to load examinations.", "danger");
  }
}

async function fetchSlots() {
  try {
    const res = await apiClient.get("/api/examiner/slots");
    slots.value = res.data.slots || [];
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to load slots.", "danger");
  }
}

async function fetchBookings() {
  try {
    const res = await apiClient.get("/api/examiner/bookings");
    bookings.value = res.data.bookings || [];
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to load bookings.", "danger");
  }
}

async function refreshAllData() {
  loading.value = true;
  clearAlert();
  try {
    await Promise.all([
      fetchDashboard(),
      fetchExaminations(),
      fetchSlots(),
      fetchBookings(),
    ]);
  } finally {
    loading.value = false;
  }
}

// ---------------------------------------------------------------------------
// Slot Handlers
// ---------------------------------------------------------------------------

function openCreateSlotModal() {
  const openExam = examinations.value.find((e) => e.slot_creation_open) || examinations.value[0];
  slotForm.value = {
    examination_id: openExam ? openExam.id : "",
    date: "",
    start_time: "10:00",
    end_time: "11:00",
    max_capacity: 1,
    meeting_link: "",
  };
  showCreateSlotModal.value = true;
}

async function handleCreateSlot() {
  formSubmitting.value = true;
  try {
    await apiClient.post("/api/examiner/slots", slotForm.value);
    showAlert("Examination slot created successfully.");
    showCreateSlotModal.value = false;
    await fetchSlots();
    await fetchDashboard();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to create slot.", "danger");
  } finally {
    formSubmitting.value = false;
  }
}

function openEditSlotModal(slot) {
  if (slot.bookings_count > 0) {
    showAlert("Cannot edit slot because student bookings already exist.", "danger");
    return;
  }
  editingSlot.value = slot;
  editSlotForm.value = {
    date: slot.date,
    start_time: slot.start_time,
    end_time: slot.end_time,
    max_capacity: slot.max_capacity,
    meeting_link: slot.meeting_link || "",
  };
  showEditSlotModal.value = true;
}

async function handleUpdateSlot() {
  if (!editingSlot.value) return;
  formSubmitting.value = true;
  try {
    await apiClient.put(`/api/examiner/slots/${editingSlot.value.id}`, editSlotForm.value);
    showAlert("Slot updated successfully.");
    showEditSlotModal.value = false;
    await fetchSlots();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to update slot.", "danger");
  } finally {
    formSubmitting.value = false;
  }
}

async function confirmDeleteSlot(slot) {
  if (slot.bookings_count > 0) {
    showAlert("Cannot delete slot because students have already booked it.", "danger");
    return;
  }
  if (!confirm(`Are you sure you want to remove slot #${slot.id} on ${slot.date}?`)) return;
  try {
    await apiClient.delete(`/api/examiner/slots/${slot.id}`);
    showAlert(`Slot #${slot.id} deleted successfully.`);
    await fetchSlots();
    await fetchDashboard();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to delete slot.", "danger");
  }
}

// ---------------------------------------------------------------------------
// Evaluation Handlers
// ---------------------------------------------------------------------------

function openEvaluationModal(booking) {
  selectedBooking.value = booking;
  rubricScores.value = {};
  evaluationForm.value = {
    marks_obtained: booking.has_evaluation ? booking.evaluation.total_marks : null,
    remarks: booking.has_evaluation ? booking.evaluation.remarks || "" : "",
  };
  showEvaluationModal.value = true;
}

async function handleSaveEvaluation() {
  if (!selectedBooking.value) return;
  formSubmitting.value = true;
  try {
    const breakdown = (selectedBooking.value.rubrics || []).map((r) => ({
      rubric_id: r.id,
      criterion_name: r.criterion_name,
      max_marks: r.max_marks,
      weightage: r.weightage,
      marks: Number(rubricScores.value[r.id] !== undefined ? rubricScores.value[r.id] : 0),
    }));

    const payload = {
      booking_id: selectedBooking.value.booking_id,
      marks_obtained: Number(evaluationForm.value.marks_obtained),
      remarks: evaluationForm.value.remarks,
      rubric_breakdown: breakdown.length > 0 ? breakdown : undefined,
    };
    const res = await apiClient.post("/api/examiner/evaluations", payload);

    // Update in-place in UI
    selectedBooking.value.status = "Completed";
    selectedBooking.value.has_evaluation = true;
    selectedBooking.value.evaluation = res.data.evaluation;

    showAlert(
      `Evaluation saved for ${selectedBooking.value.student_name}: ${payload.marks_obtained} marks recorded.`
    );
    showEvaluationModal.value = false;

    await fetchDashboard();
    await fetchBookings();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to submit evaluation.", "danger");
  } finally {
    formSubmitting.value = false;
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
