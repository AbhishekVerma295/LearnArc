-- ============================================================
--  LearnArc – Database Setup & Sample Data
--  Run this ONLY if you want pre-populated demo data.
--  The app auto-creates tables via init_db() on first run.
-- ============================================================

CREATE DATABASE IF NOT EXISTS course_platform;
USE course_platform;

-- ─── TABLES ──────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS STUDENT (
    StudentID  INT AUTO_INCREMENT PRIMARY KEY,
    FirstName  VARCHAR(100),
    LastName   VARCHAR(100),
    Email      VARCHAR(150) UNIQUE,
    Phone      VARCHAR(20),
    RegDate    DATE
);

CREATE TABLE IF NOT EXISTS STUDENT_LOGIN (
    StudentLoginID INT AUTO_INCREMENT PRIMARY KEY,
    StudentID      INT,
    Email          VARCHAR(150),
    Password       VARCHAR(255),   -- SHA-256 hash
    LastLogin      DATETIME,
    FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID)
);

CREATE TABLE IF NOT EXISTS INSTRUCTOR (
    InstructorID INT AUTO_INCREMENT PRIMARY KEY,
    FirstName    VARCHAR(100),
    LastName     VARCHAR(100),
    Email        VARCHAR(150) UNIQUE,
    Bio          TEXT
);

CREATE TABLE IF NOT EXISTS INSTRUCTOR_LOGIN (
    InstructorLoginID INT AUTO_INCREMENT PRIMARY KEY,
    InstructorID      INT,
    Email             VARCHAR(150),
    Password          VARCHAR(255),
    LastLogin         DATETIME,
    FOREIGN KEY (InstructorID) REFERENCES INSTRUCTOR(InstructorID)
);

CREATE TABLE IF NOT EXISTS COURSE (
    CourseID     INT AUTO_INCREMENT PRIMARY KEY,
    Title        VARCHAR(200),
    Description  TEXT,
    Level        ENUM('Beginner','Intermediate','Advanced'),
    CreatedDate  DATE,
    InstructorID INT,
    FOREIGN KEY (InstructorID) REFERENCES INSTRUCTOR(InstructorID)
);

CREATE TABLE IF NOT EXISTS MODULE (
    ModuleID     INT AUTO_INCREMENT PRIMARY KEY,
    CourseID     INT,
    ModuleTitle  VARCHAR(200),
    ModuleOrder  INT,
    FOREIGN KEY (CourseID) REFERENCES COURSE(CourseID)
);

CREATE TABLE IF NOT EXISTS LESSON (
    LessonID        INT AUTO_INCREMENT PRIMARY KEY,
    ModuleID        INT,
    LessonTitle     VARCHAR(200),
    LessonNumber    INT,
    DurationMinutes INT,
    ContentURL      VARCHAR(500),
    FOREIGN KEY (ModuleID) REFERENCES MODULE(ModuleID)
);

CREATE TABLE IF NOT EXISTS ENROLLMENT (
    EnrollmentID   INT AUTO_INCREMENT PRIMARY KEY,
    StudentID      INT,
    CourseID       INT,
    EnrollmentDate DATE,
    CourseStatus   ENUM('Active','Completed') DEFAULT 'Active',
    UNIQUE(StudentID, CourseID),
    FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID),
    FOREIGN KEY (CourseID)  REFERENCES COURSE(CourseID)
);

CREATE TABLE IF NOT EXISTS PROGRESS (
    ProgressID         INT AUTO_INCREMENT PRIMARY KEY,
    StudentID          INT,
    LessonID           INT,
    ProgressStatus     ENUM('Completed') DEFAULT 'Completed',
    CompletedTimestamp DATETIME,
    UNIQUE(StudentID, LessonID),
    FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID),
    FOREIGN KEY (LessonID)  REFERENCES LESSON(LessonID)
);

CREATE TABLE IF NOT EXISTS CERTIFICATE (
    CertificateID INT AUTO_INCREMENT PRIMARY KEY,
    StudentID     INT,
    CourseID      INT,
    IssueDate     DATE,
    UNIQUE(StudentID, CourseID),
    FOREIGN KEY (StudentID) REFERENCES STUDENT(StudentID),
    FOREIGN KEY (CourseID)  REFERENCES COURSE(CourseID)
);

-- ─── VIEW: Student Progress Report ───────────────────────────

DROP VIEW IF EXISTS StudentProgressReport;

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
LEFT JOIN PROGRESS p ON l.LessonID = p.LessonID AND p.StudentID = s.StudentID
GROUP BY s.StudentID, c.CourseID;

-- ─── TRIGGER: Auto-issue certificate on course completion ─────

DROP TRIGGER IF EXISTS after_enrollment_completed;

DELIMITER $$
CREATE TRIGGER after_enrollment_completed
AFTER UPDATE ON ENROLLMENT
FOR EACH ROW
BEGIN
    IF NEW.CourseStatus = 'Completed' AND OLD.CourseStatus != 'Completed' THEN
        INSERT IGNORE INTO CERTIFICATE(StudentID, CourseID, IssueDate)
        VALUES(NEW.StudentID, NEW.CourseID, CURDATE());
    END IF;
END$$
DELIMITER ;

-- ─── SAMPLE DATA ─────────────────────────────────────────────
-- Password for all demo accounts: "password123"
-- SHA-256 of "password123":
-- ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f

INSERT IGNORE INTO INSTRUCTOR(FirstName,LastName,Email,Bio) VALUES
('Priya','Sharma','priya@learnarc.com','Senior data scientist with 10 years of industry experience.'),
('Arjun','Mehta','arjun@learnarc.com','Full-stack engineer and open-source contributor.');

INSERT IGNORE INTO INSTRUCTOR_LOGIN(InstructorID,Email,Password) VALUES
(1,'priya@learnarc.com','ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
(2,'arjun@learnarc.com','ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f');

INSERT IGNORE INTO COURSE(Title,Description,Level,CreatedDate,InstructorID) VALUES
('Python for Beginners','Learn Python from scratch with hands-on exercises and real-world projects.','Beginner','2024-01-10',2),
('Data Science with Pandas','Explore data manipulation, visualization and analysis using Python and Pandas.','Intermediate','2024-02-14',1),
('Advanced SQL Mastery','Deep-dive into SQL: window functions, CTEs, query optimization and more.','Advanced','2024-03-01',1);

INSERT IGNORE INTO MODULE(CourseID,ModuleTitle,ModuleOrder) VALUES
(1,'Setup & Basics',1),(1,'Control Flow',2),(1,'Functions & OOP',3),
(2,'DataFrames Intro',1),(2,'Grouping & Merging',2),
(3,'Window Functions',1),(3,'Query Optimization',2);

INSERT IGNORE INTO LESSON(ModuleID,LessonTitle,LessonNumber,DurationMinutes,ContentURL) VALUES
(1,'Installing Python',1,10,'https://python.org'),
(1,'Variables & Types',2,15,NULL),
(1,'Your First Script',3,20,NULL),
(2,'If / Else Statements',1,12,NULL),
(2,'Loops',2,18,NULL),
(3,'Defining Functions',1,14,NULL),
(3,'Classes & Objects',2,22,NULL),
(4,'Creating DataFrames',1,15,NULL),
(4,'Selecting & Filtering',2,18,NULL),
(5,'GroupBy Operations',1,20,NULL),
(5,'Merging DataFrames',2,25,NULL),
(6,'ROW_NUMBER & RANK',1,20,NULL),
(6,'LAG & LEAD',2,18,NULL),
(7,'EXPLAIN & Indexes',1,30,NULL);

INSERT IGNORE INTO STUDENT(FirstName,LastName,Email,Phone,RegDate) VALUES
('Kavya','Reddy','kavya@example.com','9876543210','2024-03-15'),
('Rohan','Kumar','rohan@example.com','9876543211','2024-03-20');

INSERT IGNORE INTO STUDENT_LOGIN(StudentID,Email,Password) VALUES
(1,'kavya@example.com','ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f'),
(2,'rohan@example.com','ef92b778bafe771e89245b89ecbc08a44a4e166c06659911881f383d4473e94f');
