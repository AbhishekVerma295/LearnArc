from flask import Flask, render_template, request, redirect, url_for, session, flash
import mysql.connector
from datetime import datetime
import hashlib

app = Flask(__name__)
app.secret_key = 'course_platform_secret_key_2024'

# ─── DB CONNECTION ────────────────────────────────────────────────────────────

def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="root",
        database="course_platform"
    )

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def current_student():
    return session.get('student_id')

def current_instructor():
    return session.get('instructor_id')

# ─── INIT DB (run once) ───────────────────────────────────────────────────────

def init_db():
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS STUDENT (
            StudentID INT AUTO_INCREMENT PRIMARY KEY,
            FirstName VARCHAR(100),
            LastName VARCHAR(100),
            Email VARCHAR(150) UNIQUE,
            Phone VARCHAR(20),
            RegDate DATE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS STUDENT_LOGIN (
            StudentLoginID INT AUTO_INCREMENT PRIMARY KEY,
            StudentID INT,
            Email VARCHAR(150),
            Password VARCHAR(255),
            LastLogin DATETIME,
            FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS INSTRUCTOR (
            InstructorID INT AUTO_INCREMENT PRIMARY KEY,
            FirstName VARCHAR(100),
            LastName VARCHAR(100),
            Email VARCHAR(150) UNIQUE,
            Bio TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS INSTRUCTOR_LOGIN (
            InstructorLoginID INT AUTO_INCREMENT PRIMARY KEY,
            InstructorID INT,
            Email VARCHAR(150),
            Password VARCHAR(255),
            LastLogin DATETIME,
            FOREIGN KEY (InstructorID) REFERENCES INSTRUCTOR(InstructorID)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS COURSE (
            CourseID INT AUTO_INCREMENT PRIMARY KEY,
            Title VARCHAR(200),
            Description TEXT,
            Level ENUM('Beginner','Intermediate','Advanced'),
            CreatedDate DATE,
            InstructorID INT,
            FOREIGN KEY (InstructorID) REFERENCES INSTRUCTOR(InstructorID)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS MODULE (
            ModuleID INT AUTO_INCREMENT PRIMARY KEY,
            CourseID INT,
            ModuleTitle VARCHAR(200),
            ModuleOrder INT,
            FOREIGN KEY (CourseID) REFERENCES COURSE(CourseID)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS LESSON (
            LessonID INT AUTO_INCREMENT PRIMARY KEY,
            ModuleID INT,
            LessonTitle VARCHAR(200),
            LessonNumber INT,
            DurationMinutes INT,
            ContentURL VARCHAR(500),
            FOREIGN KEY (ModuleID) REFERENCES MODULE(ModuleID)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ENROLLMENT (
            EnrollmentID INT AUTO_INCREMENT PRIMARY KEY,
            StudentID INT,
            CourseID INT,
            EnrollmentDate DATE,
            CourseStatus ENUM('Active','Completed') DEFAULT 'Active',
            UNIQUE(StudentID, CourseID),
            FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID),
            FOREIGN KEY (CourseID) REFERENCES COURSE(CourseID)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS PROGRESS (
            ProgressID INT AUTO_INCREMENT PRIMARY KEY,
            StudentID INT,
            LessonID INT,
            ProgressStatus ENUM('Completed') DEFAULT 'Completed',
            CompletedTimestamp DATETIME,
            UNIQUE(StudentID, LessonID),
            FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID),
            FOREIGN KEY (LessonID) REFERENCES LESSON(LessonID)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS CERTIFICATE (
            CertificateID INT AUTO_INCREMENT PRIMARY KEY,
            StudentID INT,
            CourseID INT,
            IssueDate DATE,
            UNIQUE(StudentID, CourseID),
            FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID),
            FOREIGN KEY (CourseID) REFERENCES COURSE(CourseID)
        )
    """)

    # VIEW: Student Progress Report
    cur.execute("DROP VIEW IF EXISTS StudentProgressReport")
    cur.execute("""
        CREATE VIEW StudentProgressReport AS
        SELECT
            s.StudentID,
            CONCAT(s.FirstName,' ',s.LastName) AS StudentName,
            c.CourseID,
            c.Title AS CourseTitle,
            e.CourseStatus,
            COUNT(DISTINCT l.LessonID) AS TotalLessons,
            COUNT(DISTINCT p.LessonID) AS CompletedLessons,
            ROUND(
                IF(COUNT(DISTINCT l.LessonID)=0, 0,
                   COUNT(DISTINCT p.LessonID)*100.0/COUNT(DISTINCT l.LessonID))
            ,1) AS ProgressPct
        FROM STUDENT s
        JOIN ENROLLMENT e ON s.StudentID = e.StudentID
        JOIN COURSE c ON e.CourseID = c.CourseID
        LEFT JOIN MODULE m ON c.CourseID = m.CourseID
        LEFT JOIN LESSON l ON m.ModuleID = l.ModuleID
        LEFT JOIN PROGRESS p ON l.LessonID = p.LessonID AND p.StudentID = s.StudentID
        GROUP BY s.StudentID, c.CourseID
    """)

    # TRIGGER: Auto-issue certificate when enrollment marked Completed
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

    db.commit()
    cur.close()
    db.close()

# ─── PUBLIC ROUTES ────────────────────────────────────────────────────────────

@app.route('/')
def index():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT CourseID, Title, Level, Description FROM COURSE")
    courses = cur.fetchall()
    cur.close()
    db.close()
    return render_template('index.html', courses=courses)


@app.route('/courses')
def courses():
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("""
        SELECT c.CourseID, c.Title, c.Level, c.Description,
               CONCAT(i.FirstName,' ',i.LastName) AS InstructorName
        FROM COURSE c
        JOIN INSTRUCTOR i ON c.InstructorID = i.InstructorID
    """)
    courses = cur.fetchall()
    cur.close()
    db.close()
    return render_template('courses.html', courses=courses)


@app.route('/course/<int:course_id>')
def course_details(course_id):
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT c.*, CONCAT(i.FirstName,' ',i.LastName) AS InstructorName
        FROM COURSE c JOIN INSTRUCTOR i ON c.InstructorID=i.InstructorID
        WHERE c.CourseID=%s
    """, (course_id,))
    course = cur.fetchone()

    cur.execute("SELECT * FROM MODULE WHERE CourseID=%s ORDER BY ModuleOrder", (course_id,))
    modules = cur.fetchall()

    for mod in modules:
        cur.execute("SELECT * FROM LESSON WHERE ModuleID=%s ORDER BY LessonNumber", (mod['ModuleID'],))
        mod['lessons'] = cur.fetchall()

    enrolled = False
    completed_lessons = set()
    progress_pct = 0

    if current_student():
        sid = current_student()
        cur.execute("SELECT * FROM ENROLLMENT WHERE StudentID=%s AND CourseID=%s", (sid, course_id))
        enrolled = cur.fetchone() is not None

        cur.execute("""
            SELECT p.LessonID FROM PROGRESS p
            JOIN LESSON l ON p.LessonID=l.LessonID
            JOIN MODULE m ON l.ModuleID=m.ModuleID
            WHERE p.StudentID=%s AND m.CourseID=%s
        """, (sid, course_id))
        completed_lessons = {r['LessonID'] for r in cur.fetchall()}

        cur.execute("""
            SELECT ProgressPct FROM StudentProgressReport
            WHERE StudentID=%s AND CourseID=%s
        """, (sid, course_id))
        row = cur.fetchone()
        progress_pct = row['ProgressPct'] if row else 0

    cur.close()
    db.close()
    return render_template('course_details.html',
                           course=course,
                           modules=modules,
                           enrolled=enrolled,
                           completed_lessons=completed_lessons,
                           progress_pct=progress_pct)

# ─── AUTH ROUTES ──────────────────────────────────────────────────────────────

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = hash_password(request.form['password'])
        role = request.form['role']
        db = get_db()
        cur = db.cursor(dictionary=True)

        if role == 'student':
            cur.execute("SELECT * FROM STUDENT_LOGIN WHERE Email=%s AND Password=%s", (email, password))
            user = cur.fetchone()
            if user:
                cur.execute("UPDATE STUDENT_LOGIN SET LastLogin=%s WHERE StudentLoginID=%s",
                            (datetime.now(), user['StudentLoginID']))
                db.commit()
                session['student_id'] = user['StudentID']
                session['role'] = 'student'
                cur.execute("SELECT * FROM STUDENT WHERE StudentID=%s", (user['StudentID'],))
                s = cur.fetchone()
                session['name'] = s['FirstName']
                cur.close(); db.close()
                return redirect(url_for('student_dashboard'))
        else:
            cur.execute("SELECT * FROM INSTRUCTOR_LOGIN WHERE Email=%s AND Password=%s", (email, password))
            user = cur.fetchone()
            if user:
                cur.execute("UPDATE INSTRUCTOR_LOGIN SET LastLogin=%s WHERE InstructorLoginID=%s",
                            (datetime.now(), user['InstructorLoginID']))
                db.commit()
                session['instructor_id'] = user['InstructorID']
                session['role'] = 'instructor'
                cur.execute("SELECT * FROM INSTRUCTOR WHERE InstructorID=%s", (user['InstructorID'],))
                ins = cur.fetchone()
                session['name'] = ins['FirstName']
                cur.close(); db.close()
                return redirect(url_for('instructor_dashboard'))

        cur.close(); db.close()
        flash('Invalid credentials. Please try again.', 'error')
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fname = request.form['firstname']
        lname = request.form['lastname']
        email = request.form['email']
        phone = request.form['phone']
        password = hash_password(request.form['password'])
        role = request.form['role']
        db = get_db()
        cur = db.cursor()
        try:
            if role == 'student':
                cur.execute("""INSERT INTO STUDENT(FirstName,LastName,Email,Phone,RegDate)
                               VALUES(%s,%s,%s,%s,%s)""",
                            (fname, lname, email, phone, datetime.today().date()))
                sid = cur.lastrowid
                cur.execute("""INSERT INTO STUDENT_LOGIN(StudentID,Email,Password)
                               VALUES(%s,%s,%s)""", (sid, email, password))
            else:
                bio = request.form.get('bio', '')
                cur.execute("""INSERT INTO INSTRUCTOR(FirstName,LastName,Email,Bio)
                               VALUES(%s,%s,%s,%s)""", (fname, lname, email, bio))
                iid = cur.lastrowid
                cur.execute("""INSERT INTO INSTRUCTOR_LOGIN(InstructorID,Email,Password)
                               VALUES(%s,%s,%s)""", (iid, email, password))
            db.commit()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        except mysql.connector.IntegrityError:
            flash('Email already registered.', 'error')
        finally:
            cur.close(); db.close()
    return render_template('signup.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─── STUDENT ROUTES ───────────────────────────────────────────────────────────

@app.route('/student/dashboard')
def student_dashboard():
    if not current_student():
        return redirect(url_for('login'))
    sid = current_student()
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT c.CourseID, c.Title, c.Level, e.EnrollmentDate, e.CourseStatus,
               CONCAT(i.FirstName,' ',i.LastName) AS InstructorName
        FROM ENROLLMENT e
        JOIN COURSE c ON e.CourseID=c.CourseID
        JOIN INSTRUCTOR i ON c.InstructorID=i.InstructorID
        WHERE e.StudentID=%s
    """, (sid,))
    enrollments = cur.fetchall()

    cur.execute("""
        SELECT ProgressPct, CourseTitle, CourseStatus
        FROM StudentProgressReport WHERE StudentID=%s
    """, (sid,))
    progress_data = cur.fetchall()

    cur.execute("""
        SELECT cert.CertificateID, c.Title, cert.IssueDate
        FROM CERTIFICATE cert
        JOIN COURSE c ON cert.CourseID=c.CourseID
        WHERE cert.StudentID=%s
    """, (sid,))
    certificates = cur.fetchall()

    cur.close(); db.close()
    return render_template('student_dashboard.html',
                           enrollments=enrollments,
                           progress_data=progress_data,
                           certificates=certificates)


@app.route('/enroll/<int:course_id>', methods=['POST'])
def enroll(course_id):
    if not current_student():
        return redirect(url_for('login'))
    sid = current_student()
    db = get_db()
    cur = db.cursor()
    try:
        cur.execute("""INSERT INTO ENROLLMENT(StudentID, CourseID, EnrollmentDate, CourseStatus)
                       VALUES(%s,%s,%s,'Active')""",
                    (sid, course_id, datetime.today().date()))
        db.commit()
        flash('Successfully enrolled!', 'success')
    except mysql.connector.IntegrityError:
        flash('You are already enrolled in this course.', 'info')
    finally:
        cur.close(); db.close()
    return redirect(url_for('course_details', course_id=course_id))


@app.route('/complete_lesson/<int:lesson_id>', methods=['POST'])
def complete_lesson(lesson_id):
    if not current_student():
        return redirect(url_for('login'))
    sid = current_student()
    db = get_db()
    cur = db.cursor(dictionary=True)
    try:
        cur.execute("""INSERT IGNORE INTO PROGRESS(StudentID, LessonID, ProgressStatus, CompletedTimestamp)
                       VALUES(%s,%s,'Completed',%s)""",
                    (sid, lesson_id, datetime.now()))
        db.commit()

        # Check if course is now fully complete
        cur.execute("""
            SELECT m.CourseID FROM LESSON l
            JOIN MODULE m ON l.ModuleID=m.ModuleID
            WHERE l.LessonID=%s
        """, (lesson_id,))
        row = cur.fetchone()
        if row:
            course_id = row['CourseID']
            cur.execute("""
                SELECT COUNT(DISTINCT l.LessonID) AS Total
                FROM LESSON l JOIN MODULE m ON l.ModuleID=m.ModuleID
                WHERE m.CourseID=%s
            """, (course_id,))
            total = cur.fetchone()['Total']
            cur.execute("""
                SELECT COUNT(DISTINCT p.LessonID) AS Done
                FROM PROGRESS p
                JOIN LESSON l ON p.LessonID=l.LessonID
                JOIN MODULE m ON l.ModuleID=m.ModuleID
                WHERE m.CourseID=%s AND p.StudentID=%s
            """, (course_id, sid))
            done = cur.fetchone()['Done']
            if total > 0 and done >= total:
                cur.execute("""
                    UPDATE ENROLLMENT SET CourseStatus='Completed'
                    WHERE StudentID=%s AND CourseID=%s
                """, (sid, course_id))
                db.commit()
                flash('🎉 Course completed! Certificate issued!', 'success')
            else:
                flash('Lesson marked as complete!', 'success')
            db.commit()
            return redirect(url_for('course_details', course_id=course_id))
    except Exception as e:
        flash(str(e), 'error')
    finally:
        cur.close(); db.close()
    return redirect(url_for('student_dashboard'))

# ─── INSTRUCTOR ROUTES ────────────────────────────────────────────────────────

@app.route('/instructor/dashboard')
def instructor_dashboard():
    if not current_instructor():
        return redirect(url_for('login'))
    iid = current_instructor()
    db = get_db()
    cur = db.cursor(dictionary=True)

    cur.execute("""
        SELECT c.CourseID, c.Title, c.Level, c.CreatedDate,
               COUNT(DISTINCT e.StudentID) AS StudentCount
        FROM COURSE c
        LEFT JOIN ENROLLMENT e ON c.CourseID=e.CourseID
        WHERE c.InstructorID=%s
        GROUP BY c.CourseID
    """, (iid,))
    courses = cur.fetchall()

    cur.execute("""
        SELECT spr.StudentName, spr.CourseTitle, spr.ProgressPct,
               spr.CompletedLessons, spr.TotalLessons, spr.CourseStatus
        FROM StudentProgressReport spr
        JOIN COURSE c ON spr.CourseID=c.CourseID
        WHERE c.InstructorID=%s
        ORDER BY spr.CourseTitle, spr.StudentName
    """, (iid,))
    progress = cur.fetchall()

    cur.execute("""
        SELECT cert.CertificateID, cert.IssueDate,
               CONCAT(s.FirstName,' ',s.LastName) AS StudentName,
               c.Title AS CourseTitle
        FROM CERTIFICATE cert
        JOIN STUDENT s ON cert.StudentID=s.StudentID
        JOIN COURSE c ON cert.CourseID=c.CourseID
        WHERE c.InstructorID=%s
    """, (iid,))
    certificates = cur.fetchall()

    cur.close(); db.close()
    return render_template('instructor_dashboard.html',
                           courses=courses,
                           progress=progress,
                           certificates=certificates)


@app.route('/instructor/create_course', methods=['POST'])
def create_course():
    if not current_instructor():
        return redirect(url_for('login'))
    iid = current_instructor()
    title = request.form['title']
    description = request.form['description']
    level = request.form['level']
    db = get_db()
    cur = db.cursor()
    cur.execute("""INSERT INTO COURSE(Title,Description,Level,CreatedDate,InstructorID)
                   VALUES(%s,%s,%s,%s,%s)""",
                (title, description, level, datetime.today().date(), iid))
    db.commit()
    cur.close(); db.close()
    flash('Course created successfully!', 'success')
    return redirect(url_for('instructor_dashboard'))


@app.route('/instructor/add_module', methods=['POST'])
def add_module():
    if not current_instructor():
        return redirect(url_for('login'))
    course_id = request.form['course_id']
    module_title = request.form['module_title']
    module_order = request.form['module_order']
    db = get_db()
    cur = db.cursor()
    cur.execute("INSERT INTO MODULE(CourseID,ModuleTitle,ModuleOrder) VALUES(%s,%s,%s)",
                (course_id, module_title, module_order))
    db.commit()
    cur.close(); db.close()
    flash('Module added!', 'success')
    return redirect(url_for('instructor_dashboard'))


@app.route('/instructor/add_lesson', methods=['POST'])
def add_lesson():
    if not current_instructor():
        return redirect(url_for('login'))
    module_id = request.form['module_id']
    lesson_title = request.form['lesson_title']
    lesson_number = request.form['lesson_number']
    duration = request.form['duration']
    content_url = request.form.get('content_url', '')
    db = get_db()
    cur = db.cursor()
    cur.execute("""INSERT INTO LESSON(ModuleID,LessonTitle,LessonNumber,DurationMinutes,ContentURL)
                   VALUES(%s,%s,%s,%s,%s)""",
                (module_id, lesson_title, lesson_number, duration, content_url))
    db.commit()
    cur.close(); db.close()
    flash('Lesson added!', 'success')
    return redirect(url_for('instructor_dashboard'))


@app.route('/instructor/get_modules/<int:course_id>')
def get_modules(course_id):
    if not current_instructor():
        return redirect(url_for('login'))
    db = get_db()
    cur = db.cursor(dictionary=True)
    cur.execute("SELECT ModuleID, ModuleTitle FROM MODULE WHERE CourseID=%s ORDER BY ModuleOrder", (course_id,))
    modules = cur.fetchall()
    cur.close(); db.close()
    import json
    return json.dumps(modules)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
