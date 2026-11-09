<template>
  <div class="container-fluid py-4 px-md-4">
    <!-- Header -->
    <div class="d-flex flex-wrap justify-content-between align-items-center mb-4 pb-2 border-bottom">
      <div>
        <h2 class="h3 fw-bold mb-1 text-dark">Administrator Control Panel</h2>
        <p class="text-muted mb-0 small">
          Examination Management Portal V2 &bull; Signed in as
          <span class="fw-semibold text-primary">{{ authStore.user?.email }}</span>
          <span class="badge bg-danger ms-2">Admin</span>
        </p>
      </div>
      <div class="d-flex gap-2 mt-2 mt-sm-0">
        <button
          class="btn btn-outline-secondary btn-sm d-flex align-items-center"
          :disabled="loading"
          @click="refreshAllData"
        >
          <span v-if="loading" class="spinner-border spinner-border-sm me-1"></span>
          <span>&#x21bb; Refresh Data</span>
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

    <!-- Search Bar -->
    <div class="card shadow-sm border-0 mb-4 bg-white">
      <div class="card-body p-3">
        <div class="row g-2 align-items-center">
          <div class="col-12 col-md-3 col-lg-2">
            <select v-model="searchType" class="form-select form-select-sm">
              <option value="all">All Categories</option>
              <option value="students">Students</option>
              <option value="examiners">Examiners</option>
              <option value="courses">Courses</option>
              <option value="examinations">Examinations</option>
              <option value="bookings">Bookings</option>
            </select>
          </div>
          <div class="col-12 col-md-7 col-lg-8">
            <div class="input-group input-group-sm">
              <input
                v-model.trim="searchQuery"
                type="text"
                class="form-control"
                placeholder="Search students, examiners, course codes, exams, booking IDs..."
                @keyup.enter="handleSearch"
              />
              <button
                class="btn btn-primary"
                type="button"
                :disabled="isSearching"
                @click="handleSearch"
              >
                <span v-if="isSearching" class="spinner-border spinner-border-sm me-1"></span>
                Search
              </button>
              <button
                v-if="searchQuery || searchResults"
                class="btn btn-outline-secondary"
                type="button"
                @click="clearSearch"
              >
                Clear
              </button>
            </div>
          </div>
          <div class="col-12 col-md-2 text-md-end text-muted small">
            <span v-if="searchResults">
              Found {{ totalSearchResultsCount }} match(es)
            </span>
          </div>
        </div>

        <!-- Search Results Panel -->
        <div v-if="searchResults" class="mt-3 pt-3 border-top">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <h6 class="mb-0 fw-bold text-secondary">
              Search Results for "{{ searchResults.query }}"
            </h6>
            <button class="btn btn-sm btn-link text-decoration-none p-0" @click="clearSearch">
              &times; Close Results
            </button>
          </div>

          <div v-if="totalSearchResultsCount === 0" class="text-muted small py-2">
            No matching records found.
          </div>

          <div class="row g-2">
            <!-- Students -->
            <div v-if="searchResults.students?.length" class="col-12 col-md-6 col-lg-4">
              <div class="border rounded p-2 bg-light">
                <span class="badge bg-info text-dark mb-1">Students ({{ searchResults.students.length }})</span>
                <ul class="list-unstyled mb-0 small">
                  <li v-for="s in searchResults.students" :key="s.id" class="text-truncate">
                    #{{ s.id }} &bull; {{ s.email }}
                    <span :class="['badge ms-1', s.active ? 'bg-success' : 'bg-secondary']">
                      {{ s.active ? 'Active' : 'Inactive' }}
                    </span>
                  </li>
                </ul>
              </div>
            </div>

            <!-- Examiners -->
            <div v-if="searchResults.examiners?.length" class="col-12 col-md-6 col-lg-4">
              <div class="border rounded p-2 bg-light">
                <span class="badge bg-warning text-dark mb-1">Examiners ({{ searchResults.examiners.length }})</span>
                <ul class="list-unstyled mb-0 small">
                  <li v-for="e in searchResults.examiners" :key="e.id" class="text-truncate">
                    <strong>{{ e.name }}</strong> ({{ e.department }}) &bull; {{ e.email }}
                  </li>
                </ul>
              </div>
            </div>

            <!-- Courses -->
            <div v-if="searchResults.courses?.length" class="col-12 col-md-6 col-lg-4">
              <div class="border rounded p-2 bg-light">
                <span class="badge bg-primary mb-1">Courses ({{ searchResults.courses.length }})</span>
                <ul class="list-unstyled mb-0 small">
                  <li v-for="c in searchResults.courses" :key="c.id" class="text-truncate">
                    <strong>{{ c.code }}</strong> - {{ c.name }}
                  </li>
                </ul>
              </div>
            </div>

            <!-- Examinations -->
            <div v-if="searchResults.examinations?.length" class="col-12 col-md-6 col-lg-4">
              <div class="border rounded p-2 bg-light">
                <span class="badge bg-success mb-1">Examinations ({{ searchResults.examinations.length }})</span>
                <ul class="list-unstyled mb-0 small">
                  <li v-for="ex in searchResults.examinations" :key="ex.id" class="text-truncate">
                    #{{ ex.id }} {{ ex.name }} ({{ ex.course_code }})
                  </li>
                </ul>
              </div>
            </div>

            <!-- Bookings -->
            <div v-if="searchResults.bookings?.length" class="col-12 col-md-6 col-lg-4">
              <div class="border rounded p-2 bg-light">
                <span class="badge bg-dark mb-1">Bookings ({{ searchResults.bookings.length }})</span>
                <ul class="list-unstyled mb-0 small">
                  <li v-for="b in searchResults.bookings" :key="b.id" class="text-truncate">
                    Booking #{{ b.id }} &bull; {{ b.student_email }} ({{ b.status }})
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Summary Statistics Cards -->
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-4 col-xl-2">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-primary border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Courses</span>
            <h3 class="fw-bold my-1 text-primary">{{ stats.total_courses }}</h3>
            <small class="text-muted">Total registered</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-success border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Examinations</span>
            <h3 class="fw-bold my-1 text-success">{{ stats.total_examinations }}</h3>
            <small class="text-muted">Across all courses</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-warning border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Examiners</span>
            <h3 class="fw-bold my-1 text-warning">{{ stats.total_examiners }}</h3>
            <small class="text-muted">Provisioned staff</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-info border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Students</span>
            <h3 class="fw-bold my-1 text-info">{{ stats.total_students }}</h3>
            <small class="text-muted">Registered accounts</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-secondary border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Exam Slots</span>
            <h3 class="fw-bold my-1 text-secondary">{{ stats.total_slots }}</h3>
            <small class="text-muted">Platform slots</small>
          </div>
        </div>
      </div>
      <div class="col-6 col-md-4 col-xl-2">
        <div class="card border-0 shadow-sm h-100 bg-white border-start border-dark border-4">
          <div class="card-body p-3">
            <span class="text-muted text-uppercase fw-semibold" style="font-size: 0.72rem;">Bookings</span>
            <h3 class="fw-bold my-1 text-dark">{{ stats.total_bookings }}</h3>
            <small class="text-muted">Student reservations</small>
          </div>
        </div>
      </div>
    </div>

    <!-- Navigation Tabs -->
    <ul class="nav nav-pills mb-3 gap-2 bg-white p-2 rounded shadow-sm" role="tablist">
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'courses' ? 'active' : '']"
          type="button"
          @click="activeTab = 'courses'"
        >
          Courses &amp; Examinations
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'examiners' ? 'active' : '']"
          type="button"
          @click="activeTab = 'examiners'"
        >
          Examiner Provisioning
          <span class="badge bg-secondary ms-1">{{ examiners.length }}</span>
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'slots' ? 'active' : '']"
          type="button"
          @click="activeTab = 'slots'"
        >
          Slot Supervision &amp; Bookings
          <span class="badge bg-secondary ms-1">{{ slots.length }}</span>
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          :class="['nav-link', activeTab === 'history' ? 'active' : '']"
          type="button"
          @click="loadHistoryTab"
        >
          Historical Records
        </button>
      </li>
    </ul>

    <!-- Tab 1: Courses & Examinations -->
    <div v-show="activeTab === 'courses'" class="space-y-4">
      <!-- Courses Section -->
      <div class="card shadow-sm border-0 mb-4">
        <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
          <h5 class="mb-0 fw-bold text-dark">Course Catalog</h5>
          <button class="btn btn-primary btn-sm" @click="openAddCourseModal">
            + Add New Course
          </button>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 80px;">ID</th>
                <th style="width: 120px;">Code</th>
                <th>Course Name</th>
                <th>Description</th>
                <th style="width: 100px;">Status</th>
                <th style="width: 90px;" class="text-center">Exams</th>
                <th style="width: 140px;" class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="courses.length === 0">
                <td colspan="7" class="text-center text-muted py-4">
                  No courses found. Click "+ Add New Course" to add one.
                </td>
              </tr>
              <tr v-for="c in courses" :key="c.id">
                <td class="text-muted fw-semibold">#{{ c.id }}</td>
                <td><span class="badge bg-primary fs-6">{{ c.code }}</span></td>
                <td class="fw-semibold">{{ c.name }}</td>
                <td class="text-muted small text-truncate" style="max-width: 250px;">
                  {{ c.description || 'No description provided' }}
                </td>
                <td>
                  <span :class="['badge', c.status === 'Active' ? 'bg-success' : 'bg-secondary']">
                    {{ c.status }}
                  </span>
                </td>
                <td class="text-center">
                  <span class="badge bg-light text-dark border">{{ c.examinations_count || 0 }}</span>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-secondary" @click="openEditCourseModal(c)">
                      Edit
                    </button>
                    <button class="btn btn-outline-danger" @click="confirmDeleteCourse(c)">
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Examinations Section -->
      <div class="card shadow-sm border-0">
        <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
          <div>
            <h5 class="mb-0 fw-bold text-dark">Examinations &amp; Schedules</h5>
            <small class="text-muted">Manage timelines, types, and rubric criteria</small>
          </div>
          <button class="btn btn-success btn-sm" @click="openAddExamModal">
            + Create Examination
          </button>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 70px;">ID</th>
                <th>Exam &amp; Course</th>
                <th style="width: 110px;">Type</th>
                <th>Slot Creation Window</th>
                <th>Student Booking Window</th>
                <th style="width: 130px;">Status</th>
                <th style="width: 200px;" class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="examinations.length === 0">
                <td colspan="7" class="text-center text-muted py-4">
                  No examinations scheduled yet. Click "+ Create Examination" to configure one.
                </td>
              </tr>
              <tr v-for="e in examinations" :key="e.id">
                <td class="text-muted fw-semibold">#{{ e.id }}</td>
                <td>
                  <div class="fw-bold text-dark">{{ e.name }}</div>
                  <small class="text-primary fw-medium">{{ e.course_code }} - {{ e.course_name }}</small>
                </td>
                <td>
                  <span class="badge bg-info text-dark">{{ e.type }}</span>
                </td>
                <td class="small text-muted">
                  <div><strong>From:</strong> {{ formatDate(e.slot_creation_start_date) }}</div>
                  <div><strong>To:</strong> {{ formatDate(e.slot_creation_end_date) }}</div>
                </td>
                <td class="small text-muted">
                  <div><strong>From:</strong> {{ formatDate(e.slot_booking_start_date) }}</div>
                  <div><strong>To:</strong> {{ formatDate(e.slot_booking_end_date) }}</div>
                </td>
                <td>
                  <select
                    class="form-select form-select-sm"
                    :value="e.status"
                    @change="handleQuickStatusChange(e, $event.target.value)"
                  >
                    <option value="Scheduled">Scheduled</option>
                    <option value="Slot Creation Open">Slot Creation Open</option>
                    <option value="Slot Creation Closed">Slot Creation Closed</option>
                    <option value="Booking Open">Booking Open</option>
                    <option value="Booking Closed">Booking Closed</option>
                    <option value="Completed">Completed</option>
                    <option value="Cancelled">Cancelled</option>
                  </select>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-info" @click="openRubricsModal(e)">
                      Rubrics ({{ e.rubrics_count || e.rubrics?.length || 0 }})
                    </button>
                    <button class="btn btn-outline-secondary" @click="openEditExamModal(e)">
                      Edit
                    </button>
                    <button class="btn btn-outline-danger" @click="confirmDeleteExam(e)">
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

    <!-- Tab 2: Examiner Provisioning -->
    <div v-show="activeTab === 'examiners'">
      <div class="card shadow-sm border-0">
        <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
          <div>
            <h5 class="mb-0 fw-bold text-dark">Examiner Provisioning &amp; Status Management</h5>
            <small class="text-muted">Examiners are provisioned directly by the Administrator</small>
          </div>
          <button class="btn btn-warning btn-sm text-dark fw-semibold" @click="openAddExaminerModal">
            + Provision Examiner
          </button>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 70px;">ID</th>
                <th>Examiner Name</th>
                <th>Email Address</th>
                <th>Department</th>
                <th>Contact</th>
                <th style="width: 140px;">Profile Status</th>
                <th style="width: 100px;">Account</th>
                <th style="width: 160px;" class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="examiners.length === 0">
                <td colspan="8" class="text-center text-muted py-4">
                  No examiners provisioned yet. Click "+ Provision Examiner" above.
                </td>
              </tr>
              <tr v-for="ex in examiners" :key="ex.id">
                <td class="text-muted fw-semibold">#{{ ex.id }}</td>
                <td class="fw-bold">{{ ex.name }}</td>
                <td>{{ ex.email }}</td>
                <td>{{ ex.department }}</td>
                <td class="text-muted small">{{ ex.contact || '-' }}</td>
                <td>
                  <span
                    :class="[
                      'badge',
                      ex.status === 'Active' || ex.status === 'Approved' ? 'bg-success' : '',
                      ex.status === 'Pending' ? 'bg-warning text-dark' : '',
                      ex.status === 'Deactivated' ? 'bg-danger' : '',
                    ]"
                  >
                    {{ ex.status }}
                  </span>
                </td>
                <td>
                  <span :class="['badge', ex.active ? 'bg-success' : 'bg-secondary']">
                    {{ ex.active ? 'Active' : 'Disabled' }}
                  </span>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm">
                    <button
                      v-if="ex.active && ex.status !== 'Deactivated'"
                      class="btn btn-outline-danger"
                      @click="toggleExaminerStatus(ex, 'Deactivated', false)"
                    >
                      Deactivate
                    </button>
                    <button
                      v-else
                      class="btn btn-outline-success"
                      @click="toggleExaminerStatus(ex, 'Active', true)"
                    >
                      Activate
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Tab 3: Slots & Bookings Supervision -->
    <div v-show="activeTab === 'slots'">
      <!-- Slots Supervision Section -->
      <div class="card shadow-sm border-0 mb-4">
        <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
          <div>
            <h5 class="mb-0 fw-bold text-dark">Examination Slots Supervision</h5>
            <small class="text-muted">View all platform slots and handle emergency examiner reassignment</small>
          </div>
          <button class="btn btn-outline-secondary btn-sm" @click="fetchSlots">
            &#x21bb; Reload Slots
          </button>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 70px;">Slot ID</th>
                <th>Course / Examination</th>
                <th>Assigned Examiner</th>
                <th>Date &amp; Time</th>
                <th>Capacity</th>
                <th>Status</th>
                <th style="width: 160px;" class="text-end">Supervision</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="slots.length === 0">
                <td colspan="7" class="text-center text-muted py-4">
                  No examination slots have been created by examiners yet.
                </td>
              </tr>
              <tr v-for="s in slots" :key="s.id">
                <td class="text-muted fw-semibold">#{{ s.id }}</td>
                <td>
                  <div class="fw-bold">{{ s.examination_name }}</div>
                  <small class="text-primary">{{ s.course_code }}</small>
                </td>
                <td>
                  <div class="fw-semibold">{{ s.examiner_name || s.examiner_email }}</div>
                  <small class="text-muted">{{ s.examiner_email }}</small>
                </td>
                <td>
                  <div><strong>{{ s.date }}</strong></div>
                  <small class="text-muted">{{ s.start_time }} - {{ s.end_time }}</small>
                </td>
                <td>
                  <span class="badge bg-light text-dark border">
                    {{ s.available_seats }} / {{ s.max_capacity }} seats left
                  </span>
                  <div class="small text-muted mt-1">{{ s.bookings_count }} student(s) booked</div>
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
                  <button class="btn btn-outline-warning btn-sm text-dark" @click="openReassignModal(s)">
                    Reassign Examiner
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Bookings Rescheduling Section -->
      <div class="card shadow-sm border-0">
        <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
          <div>
            <h5 class="mb-0 fw-bold text-dark">Student Bookings &amp; Rescheduling</h5>
            <small class="text-muted">Exceptional emergency rescheduling of student examination bookings</small>
          </div>
          <button class="btn btn-outline-secondary btn-sm" @click="fetchBookings">
            &#x21bb; Reload Bookings
          </button>
        </div>
        <div class="table-responsive">
          <table class="table table-hover align-middle mb-0">
            <thead class="table-light">
              <tr>
                <th style="width: 70px;">ID</th>
                <th>Student</th>
                <th>Examination / Course</th>
                <th>Scheduled Slot</th>
                <th>Examiner</th>
                <th>Status</th>
                <th style="width: 160px;" class="text-end">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="bookings.length === 0">
                <td colspan="7" class="text-center text-muted py-4">
                  No active student bookings found.
                </td>
              </tr>
              <tr v-for="b in bookings" :key="b.id">
                <td class="text-muted fw-semibold">#{{ b.id }}</td>
                <td>
                  <div class="fw-semibold">{{ b.student_email }}</div>
                  <small class="text-muted">Student #{{ b.student_id }}</small>
                </td>
                <td>
                  <div class="fw-bold">{{ b.slot?.examination_name || 'N/A' }}</div>
                  <small class="text-primary">{{ b.slot?.course_code }}</small>
                </td>
                <td>
                  <div v-if="b.slot">
                    <strong>{{ b.slot.date }}</strong>
                    <span class="text-muted ms-1">({{ b.slot.start_time }} - {{ b.slot.end_time }})</span>
                  </div>
                  <span v-else class="text-danger small">Slot deleted/missing</span>
                </td>
                <td>
                  <div class="small fw-semibold">{{ b.slot?.examiner_name || b.slot?.examiner_email }}</div>
                </td>
                <td>
                  <span
                    :class="[
                      'badge',
                      b.status === 'Booked' ? 'bg-primary' : '',
                      b.status === 'Completed' ? 'bg-success' : '',
                      b.status === 'Cancelled' ? 'bg-danger' : '',
                    ]"
                  >
                    {{ b.status }}
                  </span>
                </td>
                <td class="text-end">
                  <button
                    class="btn btn-outline-primary btn-sm"
                    :disabled="b.status === 'Completed' || b.status === 'Cancelled'"
                    @click="openRescheduleModal(b)"
                  >
                    Reschedule
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Tab 4: Historical Records -->
    <div v-show="activeTab === 'history'">
      <div class="card shadow-sm border-0 mb-4">
        <div class="card-header bg-white py-3 d-flex justify-content-between align-items-center">
          <div>
            <h5 class="mb-0 fw-bold text-dark">Historical Records &amp; Archives</h5>
            <small class="text-muted">Full platform logs of all past and ongoing examinations</small>
          </div>
          <button class="btn btn-outline-secondary btn-sm" @click="fetchHistoryRecords">
            &#x21bb; Refresh History
          </button>
        </div>
        <div class="card-body">
          <h6 class="fw-bold text-secondary mb-3">All Recorded Examinations ({{ historyRecords.examinations?.length || 0 }})</h6>
          <div class="table-responsive mb-4">
            <table class="table table-sm table-bordered align-middle">
              <thead class="table-light">
                <tr>
                  <th>Exam ID</th>
                  <th>Course</th>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Slots</th>
                  <th>Rubrics</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!historyRecords.examinations?.length">
                  <td colspan="7" class="text-center text-muted py-3">No examination records.</td>
                </tr>
                <tr v-for="he in historyRecords.examinations" :key="he.id">
                  <td>#{{ he.id }}</td>
                  <td><span class="badge bg-primary">{{ he.course_code }}</span></td>
                  <td class="fw-semibold">{{ he.name }}</td>
                  <td>{{ he.type }}</td>
                  <td><span class="badge bg-secondary">{{ he.status }}</span></td>
                  <td>{{ he.slots_count }}</td>
                  <td>{{ he.rubrics?.length || 0 }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <h6 class="fw-bold text-secondary mb-3">All Student Bookings Log ({{ historyRecords.bookings?.length || 0 }})</h6>
          <div class="table-responsive">
            <table class="table table-sm table-bordered align-middle">
              <thead class="table-light">
                <tr>
                  <th>Booking ID</th>
                  <th>Student Email</th>
                  <th>Exam &amp; Course</th>
                  <th>Date &amp; Time</th>
                  <th>Booking Status</th>
                  <th>Evaluation / Marks</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!historyRecords.bookings?.length">
                  <td colspan="6" class="text-center text-muted py-3">No booking history logged.</td>
                </tr>
                <tr v-for="hb in historyRecords.bookings" :key="hb.id">
                  <td>#{{ hb.id }}</td>
                  <td>{{ hb.student_email }}</td>
                  <td>{{ hb.slot?.examination_name }} ({{ hb.slot?.course_code }})</td>
                  <td>{{ hb.slot?.date }} {{ hb.slot?.start_time }}</td>
                  <td><span class="badge bg-dark">{{ hb.status }}</span></td>
                  <td>
                    <span v-if="hb.has_evaluation" class="badge bg-success">
                      {{ hb.evaluation?.total_marks }} marks
                    </span>
                    <span v-else class="text-muted small">Not evaluated</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ================================================================= -->
    <!-- MODALS (Standard Bootstrap 5 Modal Markup with Reactive Vue State) -->
    <!-- ================================================================= -->

    <!-- Modal 1: Add / Edit Course -->
    <div
      v-if="showCourseModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-primary text-white">
            <h5 class="modal-title">{{ editingCourse ? 'Edit Course' : 'Add New Course' }}</h5>
            <button type="button" class="btn-close btn-close-white" @click="showCourseModal = false"></button>
          </div>
          <form @submit.prevent="handleSaveCourse">
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label fw-semibold">Course Code <span class="text-danger">*</span></label>
                <input
                  v-model.trim="courseForm.code"
                  type="text"
                  class="form-control"
                  placeholder="e.g. CS101, MAD202"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label fw-semibold">Course Name <span class="text-danger">*</span></label>
                <input
                  v-model.trim="courseForm.name"
                  type="text"
                  class="form-control"
                  placeholder="e.g. Modern Application Development II"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label fw-semibold">Description</label>
                <textarea
                  v-model.trim="courseForm.description"
                  class="form-control"
                  rows="3"
                  placeholder="Course syllabus and examination outline..."
                ></textarea>
              </div>
              <div class="mb-3">
                <label class="form-label fw-semibold">Status</label>
                <select v-model="courseForm.status" class="form-select">
                  <option value="Active">Active</option>
                  <option value="Archived">Archived</option>
                </select>
              </div>
            </div>
            <div class="modal-footer bg-light">
              <button type="button" class="btn btn-secondary" @click="showCourseModal = false">
                Cancel
              </button>
              <button type="submit" class="btn btn-primary" :disabled="formSubmitting">
                {{ formSubmitting ? 'Saving...' : 'Save Course' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Modal 2: Add / Edit Examination -->
    <div
      v-if="showExamModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog modal-lg">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-success text-white">
            <h5 class="modal-title">{{ editingExam ? 'Edit Examination' : 'Create Examination' }}</h5>
            <button type="button" class="btn-close btn-close-white" @click="showExamModal = false"></button>
          </div>
          <form @submit.prevent="handleSaveExam">
            <div class="modal-body">
              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label fw-semibold">Course <span class="text-danger">*</span></label>
                  <select v-model="examForm.course_id" class="form-select" required>
                    <option value="" disabled>-- Select Course --</option>
                    <option v-for="c in courses" :key="c.id" :value="c.id">
                      {{ c.code }} - {{ c.name }}
                    </option>
                  </select>
                </div>
                <div class="col-md-6">
                  <label class="form-label fw-semibold">Exam Type <span class="text-danger">*</span></label>
                  <select v-model="examForm.type" class="form-select" required>
                    <option value="Viva">Viva</option>
                    <option value="Practical">Practical</option>
                    <option value="Assessment">Assessment</option>
                  </select>
                </div>
                <div class="col-12">
                  <label class="form-label fw-semibold">Examination Name <span class="text-danger">*</span></label>
                  <input
                    v-model.trim="examForm.name"
                    type="text"
                    class="form-control"
                    placeholder="e.g. End-Term Project Viva Voce"
                    required
                  />
                </div>
                <div class="col-md-6">
                  <label class="form-label fw-semibold">Slot Creation Start <span class="text-danger">*</span></label>
                  <input
                    v-model="examForm.slot_creation_start_date"
                    type="datetime-local"
                    class="form-control"
                    required
                  />
                </div>
                <div class="col-md-6">
                  <label class="form-label fw-semibold">Slot Creation End <span class="text-danger">*</span></label>
                  <input
                    v-model="examForm.slot_creation_end_date"
                    type="datetime-local"
                    class="form-control"
                    required
                  />
                </div>
                <div class="col-md-6">
                  <label class="form-label fw-semibold">Student Booking Start <span class="text-danger">*</span></label>
                  <input
                    v-model="examForm.slot_booking_start_date"
                    type="datetime-local"
                    class="form-control"
                    required
                  />
                </div>
                <div class="col-md-6">
                  <label class="form-label fw-semibold">Student Booking End <span class="text-danger">*</span></label>
                  <input
                    v-model="examForm.slot_booking_end_date"
                    type="datetime-local"
                    class="form-control"
                    required
                  />
                </div>
                <div class="col-md-6">
                  <label class="form-label fw-semibold">Initial Status</label>
                  <select v-model="examForm.status" class="form-select">
                    <option value="Scheduled">Scheduled</option>
                    <option value="Slot Creation Open">Slot Creation Open</option>
                    <option value="Booking Open">Booking Open</option>
                  </select>
                </div>
              </div>
            </div>
            <div class="modal-footer bg-light">
              <button type="button" class="btn btn-secondary" @click="showExamModal = false">
                Cancel
              </button>
              <button type="submit" class="btn btn-success" :disabled="formSubmitting">
                {{ formSubmitting ? 'Saving...' : 'Save Examination' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Modal 3: Manage Rubrics -->
    <div
      v-if="showRubricModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog modal-lg">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-dark text-white">
            <h5 class="modal-title">
              Manage Rubrics: {{ selectedExamForRubrics?.name }}
            </h5>
            <button type="button" class="btn-close btn-close-white" @click="showRubricModal = false"></button>
          </div>
          <div class="modal-body">
            <div class="table-responsive mb-4">
              <table class="table table-sm table-bordered align-middle">
                <thead class="table-light">
                  <tr>
                    <th>Criterion Name</th>
                    <th style="width: 120px;">Max Marks</th>
                    <th style="width: 120px;">Weightage (%)</th>
                    <th style="width: 80px;" class="text-center">Action</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="currentRubrics.length === 0">
                    <td colspan="4" class="text-center text-muted py-3">
                      No evaluation criteria defined yet. Add criteria below.
                    </td>
                  </tr>
                  <tr v-for="r in currentRubrics" :key="r.id">
                    <td class="fw-semibold">{{ r.criterion_name }}</td>
                    <td>{{ r.max_marks }}</td>
                    <td>{{ r.weightage }}%</td>
                    <td class="text-center">
                      <button
                        class="btn btn-outline-danger btn-sm py-0 px-2"
                        @click="handleDeleteRubric(r.id)"
                      >
                        &times;
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Add Rubric Form -->
            <div class="card bg-light border p-3">
              <h6 class="fw-bold mb-3">Add Evaluation Criterion</h6>
              <form @submit.prevent="handleAddRubric">
                <div class="row g-2 align-items-end">
                  <div class="col-md-5">
                    <label class="form-label small fw-semibold">Criterion Name *</label>
                    <input
                      v-model.trim="rubricForm.criterion_name"
                      type="text"
                      class="form-control form-control-sm"
                      placeholder="e.g. Code Structure & Quality"
                      required
                    />
                  </div>
                  <div class="col-md-3">
                    <label class="form-label small fw-semibold">Max Marks *</label>
                    <input
                      v-model.number="rubricForm.max_marks"
                      type="number"
                      step="0.5"
                      min="1"
                      class="form-control form-control-sm"
                      placeholder="25"
                      required
                    />
                  </div>
                  <div class="col-md-2">
                    <label class="form-label small fw-semibold">Weightage %</label>
                    <input
                      v-model.number="rubricForm.weightage"
                      type="number"
                      step="0.5"
                      min="0"
                      class="form-control form-control-sm"
                      placeholder="50"
                      required
                    />
                  </div>
                  <div class="col-md-2">
                    <button type="submit" class="btn btn-primary btn-sm w-100" :disabled="formSubmitting">
                      + Add
                    </button>
                  </div>
                </div>
              </form>
            </div>
          </div>
          <div class="modal-footer bg-light">
            <button type="button" class="btn btn-secondary btn-sm" @click="showRubricModal = false">
              Done
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal 4: Provision Examiner -->
    <div
      v-if="showExaminerModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-warning text-dark">
            <h5 class="modal-title fw-bold">Provision New Examiner</h5>
            <button type="button" class="btn-close" @click="showExaminerModal = false"></button>
          </div>
          <form @submit.prevent="handleProvisionExaminer">
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label fw-semibold">Full Name <span class="text-danger">*</span></label>
                <input
                  v-model.trim="examinerForm.name"
                  type="text"
                  class="form-control"
                  placeholder="e.g. Dr. Alan Turing"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label fw-semibold">Official Email <span class="text-danger">*</span></label>
                <input
                  v-model.trim="examinerForm.email"
                  type="email"
                  class="form-control"
                  placeholder="examiner@portal.com"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label fw-semibold">Department <span class="text-danger">*</span></label>
                <input
                  v-model.trim="examinerForm.department"
                  type="text"
                  class="form-control"
                  placeholder="e.g. Computer Science & Engineering"
                  required
                />
              </div>
              <div class="mb-3">
                <label class="form-label fw-semibold">Contact Number</label>
                <input
                  v-model.trim="examinerForm.contact"
                  type="text"
                  class="form-control"
                  placeholder="e.g. +91 9876543210"
                />
              </div>
              <div class="mb-3">
                <label class="form-label fw-semibold">Temporary Password</label>
                <input
                  v-model.trim="examinerForm.temporary_password"
                  type="text"
                  class="form-control"
                  placeholder="Examiner@123"
                  required
                />
                <small class="text-muted">The examiner will log in using this temporary password.</small>
              </div>
            </div>
            <div class="modal-footer bg-light">
              <button type="button" class="btn btn-secondary" @click="showExaminerModal = false">
                Cancel
              </button>
              <button type="submit" class="btn btn-warning text-dark fw-semibold" :disabled="formSubmitting">
                {{ formSubmitting ? 'Provisioning...' : 'Provision Examiner' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Modal 5: Reassign Slot Examiner -->
    <div
      v-if="showReassignModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-warning text-dark">
            <h5 class="modal-title fw-bold">Reassign Slot Examiner</h5>
            <button type="button" class="btn-close" @click="showReassignModal = false"></button>
          </div>
          <form @submit.prevent="handleReassignExaminer">
            <div class="modal-body">
              <p class="small text-muted mb-3">
                Reassigning an examination slot to another examiner in exceptional circumstances.
              </p>
              <div class="mb-3">
                <label class="form-label small fw-semibold">Slot Info</label>
                <div class="p-2 border rounded bg-light small">
                  <div><strong>Slot ID:</strong> #{{ selectedSlot?.id }}</div>
                  <div><strong>Exam:</strong> {{ selectedSlot?.examination_name }} ({{ selectedSlot?.course_code }})</div>
                  <div><strong>Date &amp; Time:</strong> {{ selectedSlot?.date }} ({{ selectedSlot?.start_time }} - {{ selectedSlot?.end_time }})</div>
                  <div><strong>Current Examiner:</strong> {{ selectedSlot?.examiner_name || selectedSlot?.examiner_email }}</div>
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label fw-semibold">New Assigned Examiner <span class="text-danger">*</span></label>
                <select v-model="targetExaminerId" class="form-select" required>
                  <option value="" disabled>-- Select Replacement Examiner --</option>
                  <option
                    v-for="ex in examiners.filter(e => e.active && e.id !== selectedSlot?.examiner_id)"
                    :key="ex.id"
                    :value="ex.id"
                  >
                    {{ ex.name }} ({{ ex.email }}) - {{ ex.department }}
                  </option>
                </select>
              </div>
            </div>
            <div class="modal-footer bg-light">
              <button type="button" class="btn btn-secondary" @click="showReassignModal = false">
                Cancel
              </button>
              <button type="submit" class="btn btn-warning text-dark fw-semibold" :disabled="formSubmitting">
                {{ formSubmitting ? 'Reassigning...' : 'Confirm Reassignment' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Modal 6: Reschedule Student Booking -->
    <div
      v-if="showRescheduleModal"
      class="modal fade show d-block"
      tabindex="-1"
      style="background: rgba(0, 0, 0, 0.55);"
    >
      <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
          <div class="modal-header bg-primary text-white">
            <h5 class="modal-title">Reschedule Student Booking</h5>
            <button type="button" class="btn-close btn-close-white" @click="showRescheduleModal = false"></button>
          </div>
          <form @submit.prevent="handleRescheduleBooking">
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label small fw-semibold">Current Booking Details</label>
                <div class="p-2 border rounded bg-light small">
                  <div><strong>Booking ID:</strong> #{{ selectedBooking?.id }}</div>
                  <div><strong>Student:</strong> {{ selectedBooking?.student_email }}</div>
                  <div><strong>Exam:</strong> {{ selectedBooking?.slot?.examination_name }} ({{ selectedBooking?.slot?.course_code }})</div>
                  <div><strong>Current Slot:</strong> {{ selectedBooking?.slot?.date }} {{ selectedBooking?.slot?.start_time }}</div>
                </div>
              </div>
              <div class="mb-3">
                <label class="form-label fw-semibold">Select New Slot <span class="text-danger">*</span></label>
                <select v-model="targetSlotId" class="form-select" required>
                  <option value="" disabled>-- Select Available Alternative Slot --</option>
                  <option
                    v-for="s in availableAlternativeSlots"
                    :key="s.id"
                    :value="s.id"
                  >
                    Slot #{{ s.id }} &bull; {{ s.date }} ({{ s.start_time }}-{{ s.end_time }}) &bull; Examiner: {{ s.examiner_name }} ({{ s.available_seats }} seats left)
                  </option>
                </select>
                <div v-if="availableAlternativeSlots.length === 0" class="text-danger small mt-1">
                  No other slots with available seats found for this examination.
                </div>
              </div>
            </div>
            <div class="modal-footer bg-light">
              <button type="button" class="btn btn-secondary" @click="showRescheduleModal = false">
                Cancel
              </button>
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="formSubmitting || !targetSlotId || availableAlternativeSlots.length === 0"
              >
                {{ formSubmitting ? 'Rescheduling...' : 'Confirm Reschedule' }}
              </button>
            </div>
          </form>
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
const activeTab = ref("courses");

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

// Data Collections
const stats = ref({
  total_courses: 0,
  total_examinations: 0,
  total_examiners: 0,
  total_students: 0,
  total_slots: 0,
  total_bookings: 0,
});
const courses = ref([]);
const examinations = ref([]);
const examiners = ref([]);
const slots = ref([]);
const bookings = ref([]);
const historyRecords = ref({ examinations: [], bookings: [] });

// Search State
const searchQuery = ref("");
const searchType = ref("all");
const isSearching = ref(false);
const searchResults = ref(null);

const totalSearchResultsCount = computed(() => {
  if (!searchResults.value) return 0;
  return (
    (searchResults.value.students?.length || 0) +
    (searchResults.value.examiners?.length || 0) +
    (searchResults.value.courses?.length || 0) +
    (searchResults.value.examinations?.length || 0) +
    (searchResults.value.bookings?.length || 0)
  );
});

// Modals State
const showCourseModal = ref(false);
const editingCourse = ref(null);
const courseForm = ref({ code: "", name: "", description: "", status: "Active" });

const showExamModal = ref(false);
const editingExam = ref(null);
const examForm = ref({
  course_id: "",
  name: "",
  type: "Viva",
  slot_creation_start_date: "",
  slot_creation_end_date: "",
  slot_booking_start_date: "",
  slot_booking_end_date: "",
  status: "Scheduled",
});

const showRubricModal = ref(false);
const selectedExamForRubrics = ref(null);
const currentRubrics = ref([]);
const rubricForm = ref({ criterion_name: "", max_marks: 25, weightage: 50 });

const showExaminerModal = ref(false);
const examinerForm = ref({
  name: "",
  email: "",
  department: "",
  contact: "",
  temporary_password: "Examiner@123",
});

const showReassignModal = ref(false);
const selectedSlot = ref(null);
const targetExaminerId = ref("");

const showRescheduleModal = ref(false);
const selectedBooking = ref(null);
const targetSlotId = ref("");

const availableAlternativeSlots = computed(() => {
  if (!selectedBooking.value || !selectedBooking.value.slot) return [];
  const currentSlotId = selectedBooking.value.slot_id;
  const examId = selectedBooking.value.slot.examination_id;
  return slots.value.filter(
    (s) =>
      s.id !== currentSlotId &&
      s.examination_id === examId &&
      s.available_seats > 0 &&
      s.status !== "Cancelled"
  );
});

// ---------------------------------------------------------------------------
// API Fetchers
// ---------------------------------------------------------------------------

async function fetchStats() {
  try {
    const res = await apiClient.get("/api/admin/stats");
    stats.value = res.data;
  } catch (err) {
    console.error("Failed to load statistics:", err);
  }
}

async function fetchCourses() {
  try {
    const res = await apiClient.get("/api/admin/courses");
    courses.value = res.data.courses || [];
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to load courses.", "danger");
  }
}

async function fetchExaminations() {
  try {
    const res = await apiClient.get("/api/admin/examinations");
    examinations.value = res.data.examinations || [];
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to load examinations.", "danger");
  }
}

async function fetchExaminers() {
  try {
    const res = await apiClient.get("/api/admin/examiners");
    examiners.value = res.data.examiners || [];
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to load examiners.", "danger");
  }
}

async function fetchSlots() {
  try {
    const res = await apiClient.get("/api/admin/slots");
    slots.value = res.data.slots || [];
  } catch (err) {
    console.error("Failed to load slots:", err);
  }
}

async function fetchBookings() {
  try {
    const res = await apiClient.get("/api/admin/records/history");
    bookings.value = res.data.bookings || [];
  } catch (err) {
    console.error("Failed to load bookings:", err);
  }
}

async function fetchHistoryRecords() {
  try {
    const res = await apiClient.get("/api/admin/records/history");
    historyRecords.value = res.data;
    bookings.value = res.data.bookings || [];
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to load historical records.", "danger");
  }
}

async function refreshAllData() {
  loading.value = true;
  clearAlert();
  try {
    await Promise.all([
      fetchStats(),
      fetchCourses(),
      fetchExaminations(),
      fetchExaminers(),
      fetchSlots(),
      fetchBookings(),
    ]);
  } finally {
    loading.value = false;
  }
}

function loadHistoryTab() {
  activeTab.value = "history";
  fetchHistoryRecords();
}

// ---------------------------------------------------------------------------
// Search Actions
// ---------------------------------------------------------------------------

async function handleSearch() {
  if (!searchQuery.value) {
    clearSearch();
    return;
  }
  isSearching.value = true;
  try {
    const res = await apiClient.get(
      `/api/admin/search?query=${encodeURIComponent(searchQuery.value)}&type=${searchType.value}`
    );
    searchResults.value = res.data;
  } catch (err) {
    showAlert(err.response?.data?.message || "Search request failed.", "danger");
  } finally {
    isSearching.value = false;
  }
}

function clearSearch() {
  searchQuery.value = "";
  searchResults.value = null;
}

// ---------------------------------------------------------------------------
// Course Handlers
// ---------------------------------------------------------------------------

function openAddCourseModal() {
  editingCourse.value = null;
  courseForm.value = { code: "", name: "", description: "", status: "Active" };
  showCourseModal.value = true;
}

function openEditCourseModal(course) {
  editingCourse.value = course;
  courseForm.value = {
    code: course.code,
    name: course.name,
    description: course.description || "",
    status: course.status || "Active",
  };
  showCourseModal.value = true;
}

async function handleSaveCourse() {
  formSubmitting.value = true;
  try {
    if (editingCourse.value) {
      await apiClient.put(`/api/admin/courses/${editingCourse.value.id}`, courseForm.value);
      showAlert("Course updated successfully.");
    } else {
      await apiClient.post("/api/admin/courses", courseForm.value);
      showAlert("Course created successfully.");
    }
    showCourseModal.value = false;
    await fetchCourses();
    await fetchStats();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to save course.", "danger");
  } finally {
    formSubmitting.value = false;
  }
}

async function confirmDeleteCourse(course) {
  if (!confirm(`Are you sure you want to delete course ${course.code} (${course.name})?`)) return;
  try {
    await apiClient.delete(`/api/admin/courses/${course.id}`);
    showAlert(`Course ${course.code} deleted successfully.`);
    await fetchCourses();
    await fetchStats();
  } catch (err) {
    showAlert(err.response?.data?.message || "Could not delete course.", "danger");
  }
}

// ---------------------------------------------------------------------------
// Examination Handlers
// ---------------------------------------------------------------------------

function openAddExamModal() {
  editingExam.value = null;
  examForm.value = {
    course_id: courses.value[0]?.id || "",
    name: "",
    type: "Viva",
    slot_creation_start_date: "",
    slot_creation_end_date: "",
    slot_booking_start_date: "",
    slot_booking_end_date: "",
    status: "Scheduled",
  };
  showExamModal.value = true;
}

function openEditExamModal(exam) {
  editingExam.value = exam;
  examForm.value = {
    course_id: exam.course_id,
    name: exam.name,
    type: exam.type,
    slot_creation_start_date: exam.slot_creation_start_date ? exam.slot_creation_start_date.slice(0, 16) : "",
    slot_creation_end_date: exam.slot_creation_end_date ? exam.slot_creation_end_date.slice(0, 16) : "",
    slot_booking_start_date: exam.slot_booking_start_date ? exam.slot_booking_start_date.slice(0, 16) : "",
    slot_booking_end_date: exam.slot_booking_end_date ? exam.slot_booking_end_date.slice(0, 16) : "",
    status: exam.status,
  };
  showExamModal.value = true;
}

async function handleSaveExam() {
  formSubmitting.value = true;
  try {
    if (editingExam.value) {
      await apiClient.put(`/api/admin/examinations/${editingExam.value.id}`, examForm.value);
      showAlert("Examination updated successfully.");
    } else {
      await apiClient.post("/api/admin/examinations", examForm.value);
      showAlert("Examination created successfully.");
    }
    showExamModal.value = false;
    await fetchExaminations();
    await fetchStats();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to save examination.", "danger");
  } finally {
    formSubmitting.value = false;
  }
}

async function handleQuickStatusChange(exam, newStatus) {
  try {
    await apiClient.put(`/api/admin/examinations/${exam.id}`, { status: newStatus });
    exam.status = newStatus;
    showAlert(`Examination status set to "${newStatus}".`);
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to update examination status.", "danger");
  }
}

async function confirmDeleteExam(exam) {
  if (!confirm(`Are you sure you want to remove examination "${exam.name}"?`)) return;
  try {
    await apiClient.delete(`/api/admin/examinations/${exam.id}`);
    showAlert(`Examination "${exam.name}" removed.`);
    await fetchExaminations();
    await fetchStats();
  } catch (err) {
    showAlert(err.response?.data?.message || "Could not delete examination.", "danger");
  }
}

// ---------------------------------------------------------------------------
// Rubrics Handlers
// ---------------------------------------------------------------------------

async function openRubricsModal(exam) {
  selectedExamForRubrics.value = exam;
  rubricForm.value = { criterion_name: "", max_marks: 25, weightage: 50 };
  try {
    const res = await apiClient.get(`/api/admin/examinations/${exam.id}/rubrics`);
    currentRubrics.value = res.data.rubrics || [];
    showRubricModal.value = true;
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to fetch rubrics.", "danger");
  }
}

async function handleAddRubric() {
  if (!selectedExamForRubrics.value) return;
  formSubmitting.value = true;
  try {
    const res = await apiClient.post(
      `/api/admin/examinations/${selectedExamForRubrics.value.id}/rubrics`,
      rubricForm.value
    );
    currentRubrics.value.push(res.data.rubric);
    rubricForm.value = { criterion_name: "", max_marks: 25, weightage: 50 };
    showAlert("Evaluation rubric added.");
    await fetchExaminations();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to add rubric.", "danger");
  } finally {
    formSubmitting.value = false;
  }
}

async function handleDeleteRubric(rubricId) {
  try {
    await apiClient.delete(`/api/admin/rubrics/${rubricId}`);
    currentRubrics.value = currentRubrics.value.filter((r) => r.id !== rubricId);
    showAlert("Rubric deleted.");
    await fetchExaminations();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to delete rubric.", "danger");
  }
}

// ---------------------------------------------------------------------------
// Examiner Provisioning Handlers
// ---------------------------------------------------------------------------

function openAddExaminerModal() {
  examinerForm.value = {
    name: "",
    email: "",
    department: "",
    contact: "",
    temporary_password: "Examiner@123",
  };
  showExaminerModal.value = true;
}

async function handleProvisionExaminer() {
  formSubmitting.value = true;
  try {
    const res = await apiClient.post("/api/admin/examiners", examinerForm.value);
    showAlert(
      `Examiner provisioned! Temporary password: ${res.data.temporary_password}`
    );
    showExaminerModal.value = false;
    await fetchExaminers();
    await fetchStats();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to provision examiner.", "danger");
  } finally {
    formSubmitting.value = false;
  }
}

async function toggleExaminerStatus(examiner, newStatus, newActive) {
  try {
    await apiClient.put(`/api/admin/examiners/${examiner.id}/status`, {
      status: newStatus,
      active: newActive,
    });
    examiner.status = newStatus;
    examiner.active = newActive;
    showAlert(`Examiner ${examiner.name} marked as ${newStatus}.`);
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to update examiner status.", "danger");
  }
}

// ---------------------------------------------------------------------------
// Slot Reassignment & Booking Rescheduling Handlers
// ---------------------------------------------------------------------------

function openReassignModal(slot) {
  selectedSlot.value = slot;
  targetExaminerId.value = "";
  showReassignModal.value = true;
}

async function handleReassignExaminer() {
  if (!selectedSlot.value || !targetExaminerId.value) return;
  formSubmitting.value = true;
  try {
    const res = await apiClient.put(
      `/api/admin/slots/${selectedSlot.value.id}/reassign-examiner`,
      { examiner_id: Number(targetExaminerId.value) }
    );
    showAlert(res.data.message || "Slot examiner reassigned successfully.");
    showReassignModal.value = false;
    await fetchSlots();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to reassign examiner.", "danger");
  } finally {
    formSubmitting.value = false;
  }
}

function openRescheduleModal(booking) {
  selectedBooking.value = booking;
  targetSlotId.value = "";
  showRescheduleModal.value = true;
}

async function handleRescheduleBooking() {
  if (!selectedBooking.value || !targetSlotId.value) return;
  formSubmitting.value = true;
  try {
    const res = await apiClient.put(
      `/api/admin/bookings/${selectedBooking.value.id}/reschedule`,
      { new_slot_id: Number(targetSlotId.value) }
    );
    showAlert(res.data.message || "Booking rescheduled successfully.");
    showRescheduleModal.value = false;
    await fetchBookings();
    await fetchSlots();
  } catch (err) {
    showAlert(err.response?.data?.message || "Failed to reschedule booking.", "danger");
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
.space-y-4 > * + * {
  margin-top: 1.5rem;
}
.table th {
  font-weight: 600;
  font-size: 0.85rem;
  letter-spacing: 0.02em;
}
.table td {
  font-size: 0.9rem;
}
</style>
