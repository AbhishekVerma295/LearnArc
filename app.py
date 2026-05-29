"""
LearnArc — Online Course Progress & Analytics Platform
=======================================================
Phase 1: Security hardening and professionalization.

Changes from original:
  - Secrets loaded from environment variables via python-dotenv
  - bcrypt replaces SHA-256 for password hashing
  - Flask-WTF CSRF protection on all forms
  - Flask-Limiter rate-limits the login endpoint
  - Instructor ownership enforced on module/lesson creation
  - Student enrollment verified before marking lesson complete
  - jsonify() replaces json.dumps()
  - debug mode controlled by environment variable
  - N+1 query on course_details fixed (lessons fetched in one query)
  - DB connection/cursor pairs use a context-manager helper
"""

import os
from contextlib import contextmanager
from datetime import datetime

import bcrypt
import mysql.connector
from dotenv import load_dotenv
from flask import (Flask, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

# ─── Bootstrap ────────────────────────────────────────────────────────────────

load_dotenv()  # reads .env if present; falls back to real env vars

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-fallback-change-in-production")

# CSRF protection — every POST form must include {{ csrf_token() }} or the
# {{ form.hidden_tag() }} block.  Browser requests without a valid token get 400.
csrf = CSRFProtect(app)

# Rate limiter — uses the client IP as the key.
# Backed by in-memory storage by default (fine for a single process).
# Swap to Redis storage string when scaling horizontally.
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],          # no global limit; we set per-route limits
    storage_uri="memory://",
)

# ─── DB Configuration ─────────────────────────────────────────────────────────

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST",     "localhost"),
    "user":     os.environ.get("DB_USER",     "root"),
    "password": os.environ.get("DB_PASSWORD", "root"),
    "database": os.environ.get("DB_NAME",     "course_platform"),
}


def get_db():
    """Open a new database connection using settings from the environment."""
    return mysql.connector.connect(**DB_CONFIG)


@contextmanager
def db_cursor(dictionary=True):
    """
    Context manager that opens a connection + cursor, commits on clean exit,
    and always closes both — even if an exception is raised.

    Usage:
        with db_cursor() as (db, cur):
            cur.execute(...)
            rows = cur.fetchall()

    Why: The original code opened a connection in every route and relied on
    manual cur.close(); db.close() calls.  A context manager guarantees cleanup
    and removes ~4 lines of boilerplate from every route.
    """
    db = get_db()
    cur = db.cursor(dictionary=dictionary)
    try:
        yield db, cur
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        cur.close()
        db.close()


# ─── Password Hashing ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    """
    Hash a password with bcrypt (work factor 12).

    Why bcrypt instead of SHA-256?
    SHA-256 is a fast cryptographic hash — it can be computed billions of
    times per second on a GPU, making it easy to brute-force.  bcrypt is
    intentionally slow (work-factor controlled) and includes a per-password
    salt automatically, making rainbow-table and brute-force attacks
    computationally impractical.

    Work factor 12 is the current industry recommendation (~250ms on a modern
    CPU), providing a good balance between security and login latency.
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()


def check_password(plain: str, hashed: str) -> bool:
    """
    Constant-time comparison of a plaintext password against a bcrypt hash.
    Returns True if they match, False otherwise.

    Note: legacy SHA-256 hashes (from the old version) will simply not match,
    requiring those users to reset their password.  For a real migration you
    would run a one-time script to re-hash passwords on next login.
    """
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ─── Session Helpers ──────────────────────────────────────────────────────────

def current_student():
    return session.get("student_id")


def current_instructor():
    return session.get("instructor_id")


# ─── DB Initialisation ────────────────────────────────────────────────────────

def init_db():
    """
    Create tables, view, and trigger if they do not already exist.

    This runs once at startup.  In Phase 2 this will be replaced by Alembic
    migrations which provide proper schema versioning.
    """
    with db_cursor() as (db, cur):

        cur.execute("""
            CREATE TABLE IF NOT EXISTS STUDENT (
                StudentID INT AUTO_INCREMENT PRIMARY KEY,
                FirstName VARCHAR(100),
                LastName  VARCHAR(100),
                Email     VARCHAR(150) UNIQUE,
                Phone     VARCHAR(20),
                RegDate   DATE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS STUDENT_LOGIN (
                StudentLoginID INT AUTO_INCREMENT PRIMARY KEY,
                StudentID      INT,
                Email          VARCHAR(150),
                Password       VARCHAR(255),
                LastLogin      DATETIME,
                FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS INSTRUCTOR (
                InstructorID INT AUTO_INCREMENT PRIMARY KEY,
                FirstName    VARCHAR(100),
                LastName     VARCHAR(100),
                Email        VARCHAR(150) UNIQUE,
                Bio          TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS INSTRUCTOR_LOGIN (
                InstructorLoginID INT AUTO_INCREMENT PRIMARY KEY,
                InstructorID      INT,
                Email             VARCHAR(150),
                Password          VARCHAR(255),
                LastLogin         DATETIME,
                FOREIGN KEY (InstructorID) REFERENCES INSTRUCTOR(InstructorID)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS COURSE (
                CourseID     INT AUTO_INCREMENT PRIMARY KEY,
                Title        VARCHAR(200),
                Description  TEXT,
                Level        ENUM('Beginner','Intermediate','Advanced'),
                CreatedDate  DATE,
                InstructorID INT,
                FOREIGN KEY (InstructorID) REFERENCES INSTRUCTOR(InstructorID)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS MODULE (
                ModuleID    INT AUTO_INCREMENT PRIMARY KEY,
                CourseID    INT,
                ModuleTitle VARCHAR(200),
                ModuleOrder INT,
                FOREIGN KEY (CourseID) REFERENCES COURSE(CourseID)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS LESSON (
                LessonID        INT AUTO_INCREMENT PRIMARY KEY,
                ModuleID        INT,
                LessonTitle     VARCHAR(200),
                LessonNumber    INT,
                DurationMinutes INT,
                ContentURL      VARCHAR(500),
                FOREIGN KEY (ModuleID) REFERENCES MODULE(ModuleID)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS ENROLLMENT (
                EnrollmentID   INT AUTO_INCREMENT PRIMARY KEY,
                StudentID      INT,
                CourseID       INT,
                EnrollmentDate DATE,
                CourseStatus   ENUM('Active','Completed') DEFAULT 'Active',
                UNIQUE(StudentID, CourseID),
                FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID),
                FOREIGN KEY (CourseID)  REFERENCES COURSE(CourseID)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS PROGRESS (
                ProgressID         INT AUTO_INCREMENT PRIMARY KEY,
                StudentID          INT,
                LessonID           INT,
                ProgressStatus     ENUM('Completed') DEFAULT 'Completed',
                CompletedTimestamp DATETIME,
                UNIQUE(StudentID, LessonID),
                FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID),
                FOREIGN KEY (LessonID)  REFERENCES LESSON(LessonID)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS CERTIFICATE (
                CertificateID INT AUTO_INCREMENT PRIMARY KEY,
                StudentID     INT,
                CourseID      INT,
                IssueDate     DATE,
                UNIQUE(StudentID, CourseID),
                FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID),
                FOREIGN KEY (CourseID)  REFERENCES COURSE(CourseID)
            )
        """)

        # VIEW: re-create idempotently
        cur.execute("DROP VIEW IF EXISTS StudentProgressReport")
        cur.execute("""
            CREATE VIEW StudentProgressReport AS
            SELECT
                s.StudentID,
                CONCAT(s.FirstName,' ',s.LastName) AS StudentName,
                c.CourseID,
                c.Title AS CourseTitle,
                e.CourseStatus,
                COUNT(DISTINCT l.LessonID)  AS TotalLessons,
                COUNT(DISTINCT p.LessonID)  AS CompletedLessons,
                ROUND(
                    IF(COUNT(DISTINCT l.LessonID) = 0, 0,
                       COUNT(DISTINCT p.LessonID) * 100.0 / COUNT(DISTINCT l.LessonID))
                , 1) AS ProgressPct
            FROM STUDENT s
            JOIN ENROLLMENT e ON s.StudentID = e.StudentID
            JOIN COURSE     c ON e.CourseID  = c.CourseID
            LEFT JOIN MODULE m ON c.CourseID  = m.CourseID
            LEFT JOIN LESSON l ON m.ModuleID  = l.ModuleID
            LEFT JOIN PROGRESS p ON l.LessonID = p.LessonID
                                AND p.StudentID = s.StudentID
            GROUP BY s.StudentID, c.CourseID
        """)

        # TRIGGER: auto-issue certificate on course completion
        cur.execute("DROP TRIGGER IF EXISTS after_enrollment_completed")
        cur.execute("""
            CREATE TRIGGER after_enrollment_completed
            AFTER UPDATE ON ENROLLMENT
            FOR EACH ROW
            BEGIN
                IF NEW.CourseStatus = 'Completed' AND OLD.CourseStatus != 'Completed' THEN
                    INSERT IGNORE INTO CERTIFICATE(StudentID, CourseID, IssueDate)
                    VALUES(NEW.StudentID, NEW.CourseID, CURDATE());
                END IF;
            END
        """)


# ─── PUBLIC ROUTES ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    with db_cursor() as (_, cur):
        cur.execute("SELECT CourseID, Title, Level, Description FROM COURSE")
        courses = cur.fetchall()
    return render_template("index.html", courses=courses)


@app.route("/courses")
def courses():
    with db_cursor() as (_, cur):
        cur.execute("""
            SELECT c.CourseID, c.Title, c.Level, c.Description,
                   CONCAT(i.FirstName,' ',i.LastName) AS InstructorName
            FROM COURSE c
            JOIN INSTRUCTOR i ON c.InstructorID = i.InstructorID
        """)
        courses = cur.fetchall()
    return render_template("courses.html", courses=courses)


@app.route("/course/<int:course_id>")
def course_details(course_id):
    with db_cursor() as (_, cur):

        # Course metadata
        cur.execute("""
            SELECT c.*, CONCAT(i.FirstName,' ',i.LastName) AS InstructorName
            FROM COURSE c
            JOIN INSTRUCTOR i ON c.InstructorID = i.InstructorID
            WHERE c.CourseID = %s
        """, (course_id,))
        course = cur.fetchone()

        # ── FIX: single query fetches all modules + lessons, eliminating N+1 ──
        # Original: one query for modules, then a loop with one query per module.
        # New: JOIN everything in one round-trip, then group in Python.
        cur.execute("""
            SELECT
                m.ModuleID, m.ModuleTitle, m.ModuleOrder,
                l.LessonID, l.LessonTitle, l.LessonNumber,
                l.DurationMinutes, l.ContentURL
            FROM MODULE m
            LEFT JOIN LESSON l ON m.ModuleID = l.ModuleID
            WHERE m.CourseID = %s
            ORDER BY m.ModuleOrder, l.LessonNumber
        """, (course_id,))
        rows = cur.fetchall()

        # Build modules list with nested lessons from the flat result set
        modules_map = {}
        for row in rows:
            mid = row["ModuleID"]
            if mid not in modules_map:
                modules_map[mid] = {
                    "ModuleID":    mid,
                    "ModuleTitle": row["ModuleTitle"],
                    "ModuleOrder": row["ModuleOrder"],
                    "lessons":     [],
                }
            if row["LessonID"] is not None:
                modules_map[mid]["lessons"].append({
                    "LessonID":        row["LessonID"],
                    "LessonTitle":     row["LessonTitle"],
                    "LessonNumber":    row["LessonNumber"],
                    "DurationMinutes": row["DurationMinutes"],
                    "ContentURL":      row["ContentURL"],
                })
        modules = list(modules_map.values())

        enrolled = False
        completed_lessons = set()
        progress_pct = 0

        if current_student():
            sid = current_student()
            cur.execute(
                "SELECT 1 FROM ENROLLMENT WHERE StudentID=%s AND CourseID=%s",
                (sid, course_id),
            )
            enrolled = cur.fetchone() is not None

            if enrolled:
                cur.execute("""
                    SELECT p.LessonID
                    FROM PROGRESS p
                    JOIN LESSON l  ON p.LessonID = l.LessonID
                    JOIN MODULE m  ON l.ModuleID  = m.ModuleID
                    WHERE p.StudentID = %s AND m.CourseID = %s
                """, (sid, course_id))
                completed_lessons = {r["LessonID"] for r in cur.fetchall()}

                cur.execute("""
                    SELECT ProgressPct FROM StudentProgressReport
                    WHERE StudentID=%s AND CourseID=%s
                """, (sid, course_id))
                row = cur.fetchone()
                progress_pct = row["ProgressPct"] if row else 0

    return render_template(
        "course_details.html",
        course=course,
        modules=modules,
        enrolled=enrolled,
        completed_lessons=completed_lessons,
        progress_pct=progress_pct,
    )


# ─── AUTH ROUTES ──────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")   # brute-force protection
def login():
    """
    Rate-limited to 10 attempts per minute per IP.

    Why rate-limiting?  Without it an attacker can try thousands of passwords
    per second.  At 10/minute an online brute-force against a single account
    would take years.
    """
    if request.method == "POST":
        email    = request.form["email"].strip().lower()
        password = request.form["password"]
        role     = request.form["role"]

        with db_cursor() as (db, cur):
            if role == "student":
                cur.execute(
                    "SELECT * FROM STUDENT_LOGIN WHERE Email=%s",
                    (email,),
                )
                user = cur.fetchone()
                if user and check_password(password, user["Password"]):
                    cur.execute(
                        "UPDATE STUDENT_LOGIN SET LastLogin=%s WHERE StudentLoginID=%s",
                        (datetime.now(), user["StudentLoginID"]),
                    )
                    cur.execute(
                        "SELECT * FROM STUDENT WHERE StudentID=%s",
                        (user["StudentID"],),
                    )
                    student = cur.fetchone()
                    session["student_id"] = user["StudentID"]
                    session["role"]       = "student"
                    session["name"]       = student["FirstName"]
                    return redirect(url_for("student_dashboard"))
            else:
                cur.execute(
                    "SELECT * FROM INSTRUCTOR_LOGIN WHERE Email=%s",
                    (email,),
                )
                user = cur.fetchone()
                if user and check_password(password, user["Password"]):
                    cur.execute(
                        "UPDATE INSTRUCTOR_LOGIN SET LastLogin=%s WHERE InstructorLoginID=%s",
                        (datetime.now(), user["InstructorLoginID"]),
                    )
                    cur.execute(
                        "SELECT * FROM INSTRUCTOR WHERE InstructorID=%s",
                        (user["InstructorID"],),
                    )
                    instructor = cur.fetchone()
                    session["instructor_id"] = user["InstructorID"]
                    session["role"]          = "instructor"
                    session["name"]          = instructor["FirstName"]
                    return redirect(url_for("instructor_dashboard"))

        flash("Invalid credentials. Please try again.", "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def signup():
    if request.method == "POST":
        fname    = request.form["firstname"].strip()
        lname    = request.form["lastname"].strip()
        email    = request.form["email"].strip().lower()
        phone    = request.form.get("phone", "").strip()
        password = hash_password(request.form["password"])
        role     = request.form["role"]

        # Basic length guards matching VARCHAR column sizes
        if len(fname) > 100 or len(lname) > 100:
            flash("Name too long (max 100 characters).", "error")
            return render_template("signup.html")
        if len(email) > 150:
            flash("Email too long (max 150 characters).", "error")
            return render_template("signup.html")

        try:
            with db_cursor() as (db, cur):
                if role == "student":
                    cur.execute(
                        "INSERT INTO STUDENT(FirstName,LastName,Email,Phone,RegDate) VALUES(%s,%s,%s,%s,%s)",
                        (fname, lname, email, phone, datetime.today().date()),
                    )
                    sid = cur.lastrowid
                    cur.execute(
                        "INSERT INTO STUDENT_LOGIN(StudentID,Email,Password) VALUES(%s,%s,%s)",
                        (sid, email, password),
                    )
                else:
                    bio = request.form.get("bio", "").strip()
                    cur.execute(
                        "INSERT INTO INSTRUCTOR(FirstName,LastName,Email,Bio) VALUES(%s,%s,%s,%s)",
                        (fname, lname, email, bio),
                    )
                    iid = cur.lastrowid
                    cur.execute(
                        "INSERT INTO INSTRUCTOR_LOGIN(InstructorID,Email,Password) VALUES(%s,%s,%s)",
                        (iid, email, password),
                    )
            flash("Account created! Please log in.", "success")
            return redirect(url_for("login"))
        except mysql.connector.IntegrityError:
            flash("Email already registered.", "error")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ─── STUDENT ROUTES ───────────────────────────────────────────────────────────

@app.route("/student/dashboard")
def student_dashboard():
    if not current_student():
        return redirect(url_for("login"))
    sid = current_student()

    with db_cursor() as (_, cur):
        cur.execute("""
            SELECT c.CourseID, c.Title, c.Level, e.EnrollmentDate, e.CourseStatus,
                   CONCAT(i.FirstName,' ',i.LastName) AS InstructorName
            FROM ENROLLMENT e
            JOIN COURSE     c ON e.CourseID     = c.CourseID
            JOIN INSTRUCTOR i ON c.InstructorID = i.InstructorID
            WHERE e.StudentID = %s
        """, (sid,))
        enrollments = cur.fetchall()

        cur.execute("""
            SELECT ProgressPct, CourseTitle, CourseStatus
            FROM StudentProgressReport
            WHERE StudentID = %s
        """, (sid,))
        progress_data = cur.fetchall()

        cur.execute("""
            SELECT cert.CertificateID, c.Title, cert.IssueDate
            FROM CERTIFICATE cert
            JOIN COURSE c ON cert.CourseID = c.CourseID
            WHERE cert.StudentID = %s
        """, (sid,))
        certificates = cur.fetchall()

    return render_template(
        "student_dashboard.html",
        enrollments=enrollments,
        progress_data=progress_data,
        certificates=certificates,
    )


@app.route("/enroll/<int:course_id>", methods=["POST"])
def enroll(course_id):
    if not current_student():
        return redirect(url_for("login"))
    sid = current_student()

    try:
        with db_cursor() as (_, cur):
            cur.execute(
                "INSERT INTO ENROLLMENT(StudentID,CourseID,EnrollmentDate,CourseStatus) VALUES(%s,%s,%s,'Active')",
                (sid, course_id, datetime.today().date()),
            )
        flash("Successfully enrolled!", "success")
    except mysql.connector.IntegrityError:
        flash("You are already enrolled in this course.", "info")

    return redirect(url_for("course_details", course_id=course_id))


@app.route("/complete_lesson/<int:lesson_id>", methods=["POST"])
def complete_lesson(lesson_id):
    if not current_student():
        return redirect(url_for("login"))
    sid = current_student()

    with db_cursor() as (db, cur):

        # ── Security fix: verify the student is enrolled before marking progress ──
        # Original had no enrollment check — any student could POST to
        # /complete_lesson/<id> for a lesson in a course they never enrolled in.
        cur.execute("""
            SELECT e.EnrollmentID
            FROM ENROLLMENT e
            JOIN COURSE  c ON e.CourseID  = c.CourseID
            JOIN MODULE  m ON c.CourseID  = m.CourseID
            JOIN LESSON  l ON m.ModuleID  = l.ModuleID
            WHERE l.LessonID = %s AND e.StudentID = %s
        """, (lesson_id, sid))
        if not cur.fetchone():
            flash("You must be enrolled in this course to mark lessons complete.", "error")
            return redirect(url_for("student_dashboard"))

        try:
            cur.execute(
                "INSERT IGNORE INTO PROGRESS(StudentID,LessonID,ProgressStatus,CompletedTimestamp) VALUES(%s,%s,'Completed',%s)",
                (sid, lesson_id, datetime.now()),
            )
            db.commit()

            # Check course completion
            cur.execute("""
                SELECT m.CourseID FROM LESSON l
                JOIN MODULE m ON l.ModuleID = m.ModuleID
                WHERE l.LessonID = %s
            """, (lesson_id,))
            row = cur.fetchone()

            if row:
                course_id = row["CourseID"]
                cur.execute("""
                    SELECT COUNT(DISTINCT l.LessonID) AS Total
                    FROM LESSON l
                    JOIN MODULE m ON l.ModuleID = m.ModuleID
                    WHERE m.CourseID = %s
                """, (course_id,))
                total = cur.fetchone()["Total"]

                cur.execute("""
                    SELECT COUNT(DISTINCT p.LessonID) AS Done
                    FROM PROGRESS p
                    JOIN LESSON l ON p.LessonID = l.LessonID
                    JOIN MODULE m ON l.ModuleID  = m.ModuleID
                    WHERE m.CourseID = %s AND p.StudentID = %s
                """, (course_id, sid))
                done = cur.fetchone()["Done"]

                if total > 0 and done >= total:
                    cur.execute(
                        "UPDATE ENROLLMENT SET CourseStatus='Completed' WHERE StudentID=%s AND CourseID=%s",
                        (sid, course_id),
                    )
                    db.commit()
                    flash("🎉 Course completed! Certificate issued!", "success")
                else:
                    flash("Lesson marked as complete!", "success")

                return redirect(url_for("course_details", course_id=course_id))

        except Exception as e:
            flash(str(e), "error")

    return redirect(url_for("student_dashboard"))


# ─── INSTRUCTOR ROUTES ────────────────────────────────────────────────────────

@app.route("/instructor/dashboard")
def instructor_dashboard():
    if not current_instructor():
        return redirect(url_for("login"))
    iid = current_instructor()

    with db_cursor() as (_, cur):
        cur.execute("""
            SELECT c.CourseID, c.Title, c.Level, c.CreatedDate,
                   COUNT(DISTINCT e.StudentID) AS StudentCount
            FROM COURSE c
            LEFT JOIN ENROLLMENT e ON c.CourseID = e.CourseID
            WHERE c.InstructorID = %s
            GROUP BY c.CourseID
        """, (iid,))
        courses = cur.fetchall()

        cur.execute("""
            SELECT spr.StudentName, spr.CourseTitle, spr.ProgressPct,
                   spr.CompletedLessons, spr.TotalLessons, spr.CourseStatus
            FROM StudentProgressReport spr
            JOIN COURSE c ON spr.CourseID = c.CourseID
            WHERE c.InstructorID = %s
            ORDER BY spr.CourseTitle, spr.StudentName
        """, (iid,))
        progress = cur.fetchall()

        cur.execute("""
            SELECT cert.CertificateID, cert.IssueDate,
                   CONCAT(s.FirstName,' ',s.LastName) AS StudentName,
                   c.Title AS CourseTitle
            FROM CERTIFICATE cert
            JOIN STUDENT s ON cert.StudentID = s.StudentID
            JOIN COURSE  c ON cert.CourseID  = c.CourseID
            WHERE c.InstructorID = %s
        """, (iid,))
        certificates = cur.fetchall()

    return render_template(
        "instructor_dashboard.html",
        courses=courses,
        progress=progress,
        certificates=certificates,
    )


@app.route("/instructor/create_course", methods=["POST"])
def create_course():
    if not current_instructor():
        return redirect(url_for("login"))
    iid         = current_instructor()
    title       = request.form["title"].strip()[:200]
    description = request.form["description"].strip()
    level       = request.form["level"]

    if level not in ("Beginner", "Intermediate", "Advanced"):
        flash("Invalid course level.", "error")
        return redirect(url_for("instructor_dashboard"))

    with db_cursor() as (_, cur):
        cur.execute(
            "INSERT INTO COURSE(Title,Description,Level,CreatedDate,InstructorID) VALUES(%s,%s,%s,%s,%s)",
            (title, description, level, datetime.today().date(), iid),
        )
    flash("Course created successfully!", "success")
    return redirect(url_for("instructor_dashboard"))


@app.route("/instructor/add_module", methods=["POST"])
def add_module():
    if not current_instructor():
        return redirect(url_for("login"))
    iid          = current_instructor()
    course_id    = request.form["course_id"]
    module_title = request.form["module_title"].strip()[:200]
    module_order = request.form["module_order"]

    # ── Security fix: verify the course belongs to this instructor ──
    # Original had no ownership check — any logged-in instructor could POST
    # another instructor's course_id and add modules to it.
    with db_cursor() as (_, cur):
        cur.execute(
            "SELECT 1 FROM COURSE WHERE CourseID=%s AND InstructorID=%s",
            (course_id, iid),
        )
        if not cur.fetchone():
            flash("You do not have permission to modify this course.", "error")
            return redirect(url_for("instructor_dashboard"))

        cur.execute(
            "INSERT INTO MODULE(CourseID,ModuleTitle,ModuleOrder) VALUES(%s,%s,%s)",
            (course_id, module_title, module_order),
        )
    flash("Module added!", "success")
    return redirect(url_for("instructor_dashboard"))


@app.route("/instructor/add_lesson", methods=["POST"])
def add_lesson():
    if not current_instructor():
        return redirect(url_for("login"))
    iid          = current_instructor()
    module_id    = request.form["module_id"]
    lesson_title = request.form["lesson_title"].strip()[:200]
    lesson_number = request.form["lesson_number"]
    duration     = request.form["duration"]
    content_url  = request.form.get("content_url", "").strip()

    # ── Security fix: verify the module's parent course belongs to this instructor ──
    with db_cursor() as (_, cur):
        cur.execute("""
            SELECT c.CourseID FROM MODULE m
            JOIN COURSE c ON m.CourseID = c.CourseID
            WHERE m.ModuleID = %s AND c.InstructorID = %s
        """, (module_id, iid))
        if not cur.fetchone():
            flash("You do not have permission to modify this module.", "error")
            return redirect(url_for("instructor_dashboard"))

        # Validate content_url scheme (allow empty or http/https only)
        if content_url:
            from urllib.parse import urlparse
            parsed = urlparse(content_url)
            if parsed.scheme not in ("http", "https"):
                flash("Content URL must be http or https.", "error")
                return redirect(url_for("instructor_dashboard"))

        cur.execute(
            "INSERT INTO LESSON(ModuleID,LessonTitle,LessonNumber,DurationMinutes,ContentURL) VALUES(%s,%s,%s,%s,%s)",
            (module_id, lesson_title, lesson_number, duration, content_url or None),
        )
    flash("Lesson added!", "success")
    return redirect(url_for("instructor_dashboard"))


@app.route("/instructor/get_modules/<int:course_id>")
def get_modules(course_id):
    """
    Returns module list as JSON for the Add Lesson modal's dynamic dropdown.

    Fixed: was using json.dumps() which bypasses Flask's response handling.
    jsonify() correctly sets Content-Type: application/json.

    Security: still verifies the instructor owns this course before returning data.
    """
    if not current_instructor():
        return jsonify({"error": "Unauthorized"}), 401

    iid = current_instructor()
    with db_cursor() as (_, cur):
        # Ownership check
        cur.execute(
            "SELECT 1 FROM COURSE WHERE CourseID=%s AND InstructorID=%s",
            (course_id, iid),
        )
        if not cur.fetchone():
            return jsonify({"error": "Forbidden"}), 403

        cur.execute(
            "SELECT ModuleID, ModuleTitle FROM MODULE WHERE CourseID=%s ORDER BY ModuleOrder",
            (course_id,),
        )
        modules = cur.fetchall()

    return jsonify(modules)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    # debug is now environment-controlled — never hardcoded True
    app.run(
        debug=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
    )
