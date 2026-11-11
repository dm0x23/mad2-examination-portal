import os
import csv
import json
import uuid
from datetime import datetime, date, timedelta, timezone
from flask import has_app_context

try:
    from backend.config import Config
    from backend.database import db
    from backend.models import (
        User,
        ExaminerProfile,
        Course,
        Examination,
        ExaminationSlot,
        Booking,
        Evaluation,
    )
    from backend.tasks.celery_app import celery_app
except ImportError:
    from config import Config
    from database import db
    from models import (
        User,
        ExaminerProfile,
        Course,
        Examination,
        ExaminationSlot,
        Booking,
        Evaluation,
    )
    from tasks.celery_app import celery_app


def with_app_context(fn):
    def wrapper(*args, **kwargs):
        if has_app_context():
            return fn(*args, **kwargs)
        try:
            from backend.app import app
        except ImportError:
            from app import app
        with app.app_context():
            return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper



@celery_app.task(name="backend.tasks.jobs.send_daily_exam_reminders")
@with_app_context
def send_daily_exam_reminders(target_date_str=None):
    os.makedirs(Config.LOGS_FOLDER, exist_ok=True)
    reminders_log_path = os.path.join(Config.LOGS_FOLDER, "reminders.log")

    if target_date_str:
        try:
            target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = date.today() + timedelta(days=1)
    else:
        target_date = date.today() + timedelta(days=1)

    tomorrow_bookings = (
        Booking.query.join(ExaminationSlot)
        .filter(
            Booking.status == "Booked",
            ExaminationSlot.date == target_date,
        )
        .all()
    )

    dispatched_reminders = []
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(reminders_log_path, "a", encoding="utf-8") as log_file:
        if not tomorrow_bookings:
            no_reminders_msg = f"[{timestamp_str}] [EXAM REMINDERS] No active bookings found for target date {target_date}. 0 reminders needed.\n"
            print(no_reminders_msg.strip())
            log_file.write(no_reminders_msg)
        else:
            for b in tomorrow_bookings:
                student = b.student
                slot = b.slot
                exam = slot.examination if slot else None
                course = exam.course if exam else None
                examiner = slot.examiner if slot else None
                examiner_profile = examiner.examiner_profile if examiner else None

                student_email = student.email if student else "unknown@portal.com"
                student_name = student_email.split("@")[0].title()
                exam_name = exam.name if exam else "Examination"
                course_code = course.code if course else "COURSE"
                slot_date_str = slot.date.isoformat() if slot and slot.date else str(target_date)
                start_str = slot.start_time.strftime("%H:%M") if slot and slot.start_time else "00:00"
                end_str = slot.end_time.strftime("%H:%M") if slot and slot.end_time else "00:00"
                meeting_link = slot.meeting_link or "https://meet.google.com/portal-exam-slot"
                examiner_name = (
                    examiner_profile.name
                    if examiner_profile
                    else (examiner.email if examiner else "Assigned Examiner")
                )

                reminder_payload = {
                    "booking_id": b.id,
                    "student_id": b.student_id,
                    "student_email": student_email,
                    "student_name": student_name,
                    "exam_name": exam_name,
                    "course_code": course_code,
                    "slot_date": slot_date_str,
                    "start_time": start_str,
                    "end_time": end_str,
                    "examiner_name": examiner_name,
                    "meeting_link": meeting_link,
                    "dispatched_at": timestamp_str,
                }

                formatted_message = (
                    f"\n{'='*70}\n"
                    f"[{timestamp_str}] [EXAM REMINDER NOTIFICATION]\n"
                    f"To: {student_name} <{student_email}>\n"
                    f"Subject: Reminder: Tomorrow's Examination - {course_code}: {exam_name}\n"
                    f"Date: {slot_date_str} | Time: {start_str} - {end_str}\n"
                    f"Examiner: {examiner_name}\n"
                    f"Join URL / Instructions: {meeting_link}\n"
                    f"Status: Confirmed | Booking ID: #{b.id}\n"
                    f"{'='*70}\n"
                )

                log_file.write(formatted_message)
                print(formatted_message)
                dispatched_reminders.append(reminder_payload)

            print(f"[{timestamp_str}] [EXAM REMINDERS] Dispatched {len(dispatched_reminders)} reminder(s) for examinations on {target_date}.")

    summary = {
        "status": "SUCCESS",
        "target_date": target_date.isoformat(),
        "total_reminders_dispatched": len(dispatched_reminders),
        "dispatched_reminders": dispatched_reminders,
        "log_path": reminders_log_path,
        "executed_at": timestamp_str,
    }
    return summary




@celery_app.task(name="backend.tasks.jobs.generate_monthly_admin_report")
@with_app_context
def generate_monthly_admin_report(year=None, month=None):
    os.makedirs(Config.REPORTS_FOLDER, exist_ok=True)
    os.makedirs(Config.LOGS_FOLDER, exist_ok=True)
    admin_log_path = os.path.join(Config.LOGS_FOLDER, "admin_reports.log")

    now = datetime.now()
    if year is None or month is None:
        first_of_this_month = date(now.year, now.month, 1)
        last_of_prev_month = first_of_this_month - timedelta(days=1)
        target_year = last_of_prev_month.year
        target_month = last_of_prev_month.month
    else:
        target_year = int(year)
        target_month = int(month)

    start_date = date(target_year, target_month, 1)
    if target_month == 12:
        next_month_start = date(target_year + 1, 1, 1)
    else:
        next_month_start = date(target_year, target_month + 1, 1)
    end_date = next_month_start - timedelta(days=1)

    total_examinations = Examination.query.count()
    exams_in_month = (
        Examination.query.join(ExaminationSlot)
        .filter(ExaminationSlot.date >= start_date, ExaminationSlot.date <= end_date)
        .distinct()
        .all()
    )

    completed_bookings_month = (
        Booking.query.join(ExaminationSlot)
        .filter(
            Booking.status == "Completed",
            ExaminationSlot.date >= start_date,
            ExaminationSlot.date <= end_date,
        )
        .count()
    )
    total_completed_bookings = Booking.query.filter_by(status="Completed").count()

    evaluations_in_month = (
        Evaluation.query.filter(
            Evaluation.evaluation_date >= datetime.combine(start_date, datetime.min.time()),
            Evaluation.evaluation_date <= datetime.combine(end_date, datetime.max.time()),
        ).all()
    )
    total_evaluations_count = Evaluation.query.count()

    pending_evaluations_count = (
        Booking.query.filter(
            Booking.status == "Booked",
            ~Booking.id.in_(db.session.query(Evaluation.booking_id)),
        ).count()
    )

    examiners = User.query.filter_by(role="Examiner").all()
    examiner_metrics = []
    for ex in examiners:
        profile = ex.examiner_profile
        evals = Evaluation.query.filter_by(examiner_id=ex.id).all()
        slots_count = ExaminationSlot.query.filter_by(examiner_id=ex.id).count()
        avg_score = (
            round(sum(e.total_marks for e in evals) / len(evals), 2)
            if evals
            else 0.0
        )
        examiner_metrics.append({
            "examiner_id": ex.id,
            "name": profile.name if profile else ex.email,
            "email": ex.email,
            "department": profile.department if profile else "N/A",
            "evaluations_completed": len(evals),
            "slots_hosted": slots_count,
            "average_score": avg_score,
        })

    examiner_metrics.sort(key=lambda x: x["evaluations_completed"], reverse=True)
    top_examiners = examiner_metrics[:5]

    filename = f"monthly_report_{target_year}_{target_month:02d}.html"
    report_file_path = os.path.join(Config.REPORTS_FOLDER, filename)
    generated_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    examiner_table_rows = "".join(
        f"""<tr>
            <td><strong>{e['name']}</strong><br><small class="text-muted">{e['email']}</small></td>
            <td>{e['department']}</td>
            <td><span class="badge bg-primary">{e['evaluations_completed']}</span></td>
            <td>{e['slots_hosted']}</td>
            <td><strong>{e['average_score']} / 100</strong></td>
        </tr>"""
        for e in top_examiners
    ) if top_examiners else "<tr><td colspan='5' class='text-center text-muted'>No examiner activity recorded</td></tr>"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monthly Examination Report - {target_year}/{target_month:02d}</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <style>
        body {{ background-color: #f8fafc; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; color: #1e293b; }}
        .header-card {{ background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%); color: #ffffff; border-radius: 12px; padding: 2.5rem; margin-bottom: 2rem; }}
        .metric-card {{ background: #ffffff; border-radius: 10px; border: 1px solid #e2e8f0; padding: 1.5rem; transition: transform 0.2s ease; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .metric-value {{ font-size: 2.25rem; font-weight: 700; color: #0f172a; margin-top: 0.5rem; }}
        .table-card {{ background: #ffffff; border-radius: 10px; border: 1px solid #e2e8f0; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
        .table-card thead {{ background-color: #f1f5f9; }}
    </style>
</head>
<body class="py-5">
    <div class="container" style="max-width: 960px;">
        <!-- Header -->
        <div class="header-card shadow">
            <span class="badge bg-light text-primary px-3 py-2 fw-semibold mb-3">EXAMINATION MANAGEMENT PORTAL V2</span>
            <h1 class="display-6 fw-bold mb-2">Monthly Administrative Report</h1>
            <p class="lead mb-0 text-white-50">
                Reporting Period: <strong>{start_date.strftime('%B %d, %Y')} – {end_date.strftime('%B %d, %Y')}</strong>
            </p>
            <div class="mt-3 small text-white-50">
                Generated automatically by Celery Beat scheduler on {generated_at_str}
            </div>
        </div>

        <!-- Metrics Grid -->
        <div class="row g-3 mb-4">
            <div class="col-md-3">
                <div class="metric-card h-100">
                    <div class="text-muted text-uppercase fw-semibold small">Examinations Active</div>
                    <div class="metric-value text-primary">{len(exams_in_month)}</div>
                    <div class="small text-muted mt-1">{total_examinations} total catalog exams</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card h-100">
                    <div class="text-muted text-uppercase fw-semibold small">Students Evaluated</div>
                    <div class="metric-value text-success">{len(evaluations_in_month)}</div>
                    <div class="small text-muted mt-1">{total_evaluations_count} all-time evaluations</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card h-100">
                    <div class="text-muted text-uppercase fw-semibold small">Completed Bookings</div>
                    <div class="metric-value text-info">{completed_bookings_month}</div>
                    <div class="small text-muted mt-1">{total_completed_bookings} total completed</div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="metric-card h-100">
                    <div class="text-muted text-uppercase fw-semibold small">Pending Evaluations</div>
                    <div class="metric-value text-warning">{pending_evaluations_count}</div>
                    <div class="small text-muted mt-1">Awaiting score submission</div>
                </div>
            </div>
        </div>

        <!-- Top Performing Examiners -->
        <div class="table-card mb-4">
            <div class="p-3 border-bottom d-flex justify-content-between align-items-center">
                <h5 class="fw-bold mb-0">Top Examiners by Evaluation Activity</h5>
                <span class="badge bg-secondary">Top {len(top_examiners)}</span>
            </div>
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0">
                    <thead>
                        <tr>
                            <th class="ps-3">Examiner</th>
                            <th>Department</th>
                            <th>Evaluations</th>
                            <th>Slots Hosted</th>
                            <th>Avg Marks</th>
                        </tr>
                    </thead>
                    <tbody class="ps-3">
                        {examiner_table_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- System Summary Footer -->
        <div class="card border-0 bg-transparent text-center text-muted small mt-4">
            <p>
                Confidential Report &copy; {target_year} Examination Management Portal V2. All rights reserved.
                <br>Delivered automatically to <strong>admin@portal.com</strong>.
            </p>
        </div>
    </div>
</body>
</html>
"""

    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    alert_message = (
        f"\n{'='*70}\n"
        f"[{generated_at_str}] [MONTHLY ADMIN REPORT DISPATCH]\n"
        f"To: System Administrator <admin@portal.com>\n"
        f"Subject: Monthly Examination Summary Report - {target_year}/{target_month:02d}\n"
        f"Report Location: {report_file_path}\n"
        f"Metrics Overview:\n"
        f"  - Active Exams in Period: {len(exams_in_month)}\n"
        f"  - Students Evaluated: {len(evaluations_in_month)} (All-time: {total_evaluations_count})\n"
        f"  - Completed Bookings: {completed_bookings_month} (All-time: {total_completed_bookings})\n"
        f"  - Pending Evaluations: {pending_evaluations_count}\n"
        f"  - Top Examiner: {top_examiners[0]['name'] if top_examiners else 'None'}\n"
        f"{'='*70}\n"
    )

    with open(admin_log_path, "a", encoding="utf-8") as log_file:
        log_file.write(alert_message)
    print(alert_message)

    return {
        "status": "SUCCESS",
        "target_period": f"{target_year}-{target_month:02d}",
        "report_filename": filename,
        "report_path": report_file_path,
        "metrics": {
            "exams_in_month": len(exams_in_month),
            "evaluations_in_month": len(evaluations_in_month),
            "total_evaluations": total_evaluations_count,
            "completed_bookings_month": completed_bookings_month,
            "pending_evaluations": pending_evaluations_count,
        },
        "generated_at": generated_at_str,
    }



@celery_app.task(bind=True, name="backend.tasks.jobs.export_student_history_csv")
@with_app_context
def export_student_history_csv(self, student_id: int):
    os.makedirs(Config.EXPORTS_FOLDER, exist_ok=True)

    bookings = (
        Booking.query.filter_by(student_id=student_id)
        .order_by(Booking.booking_date.desc())
        .all()
    )

    unique_suffix = f"{int(datetime.now().timestamp())}_{uuid.uuid4().hex[:6]}"
    filename = f"export_{student_id}_{unique_suffix}.csv"
    file_path = os.path.join(Config.EXPORTS_FOLDER, filename)

    headers = [
        "Student ID",
        "Examination Name",
        "Course Code",
        "Course Name",
        "Examination Date",
        "Start Time",
        "Examiner Name",
        "Marks Obtained",
        "Booking Status",
    ]

    rows = []
    for b in bookings:
        slot = b.slot
        exam = slot.examination if slot else None
        course = exam.course if exam else None
        examiner = slot.examiner if slot else None
        examiner_profile = examiner.examiner_profile if examiner else None

        student_id_val = str(b.student_id)
        exam_name = exam.name if exam else "N/A"
        course_code = course.code if course else "N/A"
        course_name = course.name if course else "N/A"
        exam_date = slot.date.isoformat() if slot and slot.date else "N/A"
        start_time = slot.start_time.strftime("%H:%M") if slot and slot.start_time else "N/A"
        examiner_name = (
            examiner_profile.name
            if examiner_profile
            else (examiner.email if examiner else "N/A")
        )
        marks_obtained = (
            str(b.evaluation.total_marks)
            if b.evaluation and b.evaluation.total_marks is not None
            else "N/A"
        )
        booking_status = b.status or "Booked"

        rows.append([
            student_id_val,
            exam_name,
            course_code,
            course_name,
            exam_date,
            start_time,
            examiner_name,
            marks_obtained,
            booking_status,
        ])

    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        writer.writerows(rows)

    return {
        "status": "SUCCESS",
        "student_id": student_id,
        "filename": filename,
        "download_url": f"/api/student/export-download/{filename}",
        "total_records": len(rows),
        "exported_at": datetime.now().isoformat(),
    }

