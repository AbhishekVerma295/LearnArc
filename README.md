# LearnArc — Online Course Progress & Analytics Platform
### DBMS Project | Flask + MySQL

---

## Project Structure

```
project/
├── app.py                        ← Flask backend (all routes + DB logic)
├── setup.sql                     ← SQL schema + sample data (optional)
├── README.md
├── templates/
│   ├── index.html                ← Public homepage with course listing
│   ├── login.html                ← Login (student/instructor toggle)
│   ├── signup.html               ← Signup (student/instructor)
│   ├── courses.html              ← Full course catalog with filter
│   ├── course_details.html       ← Course page with modules & lessons
│   ├── student_dashboard.html    ← Student portal (progress, certs)
│   └── instructor_dashboard.html ← Instructor portal (create, manage)
└── static/
    └── style.css                 ← Complete custom CSS
```

---

## Setup Instructions

### 1. Install dependencies

```bash
pip install flask mysql-connector-python
```

### 2. Configure MySQL

Open `app.py` and update the DB config in `get_db()`:

```python
host     = "localhost"
user     = "root"
password = "YOUR_MYSQL_PASSWORD"   ← change this
database = "course_platform"
```

### 3. Create the database

```sql
CREATE DATABASE course_platform;
```

Then (optional) load sample data:

```bash
mysql -u root -p course_platform < setup.sql
```

### 4. Run the app

```bash
python app.py
```

Visit: **http://localhost:5000**

---

## Demo Accounts (if setup.sql loaded)

| Role       | Email                   | Password     |
|------------|-------------------------|--------------|
| Student    | kavya@example.com       | password123  |
| Student    | rohan@example.com       | password123  |
| Instructor | priya@learnarc.com      | password123  |
| Instructor | arjun@learnarc.com      | password123  |

---

## Database Features Implemented

| Feature          | Implementation |
|------------------|----------------|
| **Tables**       | STUDENT, STUDENT_LOGIN, INSTRUCTOR, INSTRUCTOR_LOGIN, COURSE, MODULE, LESSON, ENROLLMENT, PROGRESS, CERTIFICATE |
| **Foreign Keys** | All relational links enforced |
| **UNIQUE**       | ENROLLMENT(StudentID, CourseID), PROGRESS(StudentID, LessonID) |
| **VIEW**         | `StudentProgressReport` — joins 6 tables, calculates ProgressPct |
| **TRIGGER**      | `after_enrollment_completed` — auto-inserts certificate when status = 'Completed' |
| **SELECT**       | Courses, modules, lessons, progress, certificates |
| **INSERT**       | Enrollment, progress, course/module/lesson creation |
| **UPDATE**       | CourseStatus → 'Completed' when all lessons done |
| **Aggregation**  | COUNT, SUM, ROUND, GROUP BY for analytics |
| **Joins**        | Multi-table joins throughout |

---

## System Flow

```
User visits /         → browses courses (public)
User signs up         → creates Student or Instructor account
Student logs in       → redirected to /student/dashboard
Student enrolls       → INSERT INTO ENROLLMENT
Student marks lesson  → INSERT INTO PROGRESS
App checks progress   → CompletedLessons / TotalLessons
If 100% done          → UPDATE ENROLLMENT SET CourseStatus='Completed'
TRIGGER fires         → INSERT INTO CERTIFICATE (auto)
Certificate appears   → in /student/dashboard → Certificates tab

Instructor logs in    → /instructor/dashboard
Creates course        → INSERT INTO COURSE
Adds module           → INSERT INTO MODULE
Adds lesson           → INSERT INTO LESSON
Views analytics       → StudentProgressReport VIEW + joins
```

---

## Key SQL Queries

```sql
-- Student progress (VIEW)
SELECT * FROM StudentProgressReport WHERE StudentID = ?;

-- Course curriculum
SELECT m.*, l.* FROM MODULE m
LEFT JOIN LESSON l ON m.ModuleID = l.ModuleID
WHERE m.CourseID = ?;

-- Enroll student
INSERT INTO ENROLLMENT(StudentID, CourseID, EnrollmentDate, CourseStatus)
VALUES(?, ?, CURDATE(), 'Active');

-- Mark lesson complete
INSERT IGNORE INTO PROGRESS(StudentID, LessonID, ProgressStatus, CompletedTimestamp)
VALUES(?, ?, 'Completed', NOW());

-- Mark course complete (triggers certificate via TRIGGER)
UPDATE ENROLLMENT SET CourseStatus='Completed'
WHERE StudentID=? AND CourseID=?;
```
