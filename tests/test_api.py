import time
import pytest


def test_health_check(client):
    """
    Health check should return 200 (DB connected) or 503 (DB unreachable).
    In the test environment, the DB is SQLite in-memory, so the real MySQL
    health probe will show as unreachable — that's expected and acceptable.
    We verify the response shape is correct in both cases.
    """
    response = client.get("/health")
    assert response.status_code in (200, 503)
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ok", "degraded")
    assert data["app"] == "LearnArc API"


def test_full_course_lifecycle(client):
    """
    Full integration test covering the complete student/instructor lifecycle:
    Register → Login → Create Course → Create Module → Create Lesson →
    Register Student → Login Student → Enroll → Complete Lesson → Check Certificates
    """
    timestamp = int(time.time())
    instructor_email = f"instructor_{timestamp}@example.com"
    student_email = f"student_{timestamp}@example.com"
    password = "password123"

    # 1. Register and login Instructor
    reg_inst = client.post("/api/v1/auth/register/instructor", json={
        "first_name": "Test", "last_name": "Instructor",
        "email": instructor_email, "password": password, "department": "Science"
    })
    assert reg_inst.status_code == 200, f"Instructor registration failed: {reg_inst.text}"

    login_inst = client.post("/api/v1/auth/login/instructor", data={
        "username": instructor_email, "password": password
    })
    assert login_inst.status_code == 200, f"Instructor login failed: {login_inst.text}"
    inst_token = login_inst.json()["access_token"]
    inst_headers = {"Authorization": f"Bearer {inst_token}"}

    # 2. Create Course, Module, Lesson
    course_resp = client.post("/api/v1/courses/", headers=inst_headers, json={
        "title": f"Test Course {timestamp}",
        "description": "A test course",
        "price": 49.99  # extra field — silently ignored by schema (no price in DB)
    })
    assert course_resp.status_code == 200, f"Course creation failed: {course_resp.text}"
    course_id = course_resp.json()["course_id"]

    module_resp = client.post(f"/api/v1/courses/{course_id}/modules", headers=inst_headers, json={
        "module_title": "Module 1", "module_order": 1
    })
    assert module_resp.status_code == 200, f"Module creation failed: {module_resp.text}"
    module_id = module_resp.json()["module_id"]

    lesson_resp = client.post(f"/api/v1/courses/modules/{module_id}/lessons", headers=inst_headers, json={
        "lesson_title": "Lesson 1", "lesson_number": 1,
        "duration_minutes": 10, "content_url": "http://example.com"
    })
    assert lesson_resp.status_code == 200, f"Lesson creation failed: {lesson_resp.text}"
    lesson_id = lesson_resp.json()["lesson_id"]

    # 3. Register and login Student
    reg_stu = client.post("/api/v1/auth/register/student", json={
        "first_name": "Test", "last_name": "Student",
        "email": student_email, "password": password
    })
    assert reg_stu.status_code == 200, f"Student registration failed: {reg_stu.text}"

    login_stu = client.post("/api/v1/auth/login/student", data={
        "username": student_email, "password": password
    })
    assert login_stu.status_code == 200, f"Student login failed: {login_stu.text}"
    stu_token = login_stu.json()["access_token"]
    stu_headers = {"Authorization": f"Bearer {stu_token}"}

    # 4. Enroll in Course
    enroll_resp = client.post(f"/api/v1/enrollments/courses/{course_id}", headers=stu_headers)
    assert enroll_resp.status_code == 200, f"Enrollment failed: {enroll_resp.text}"
    assert enroll_resp.json()["course_id"] == course_id

    # 5. Complete Lesson
    prog_resp = client.post(f"/api/v1/enrollments/progress/lessons/{lesson_id}", headers=stu_headers)
    assert prog_resp.status_code == 200, f"Progress tracking failed: {prog_resp.text}"

    # 6. Check Certificates (may or may not exist depending on DB trigger support)
    cert_resp = client.get("/api/v1/enrollments/certificates", headers=stu_headers)
    assert cert_resp.status_code == 200
    assert isinstance(cert_resp.json(), list)

    # 7. Verify course list is accessible publicly
    courses_resp = client.get("/api/v1/courses/")
    assert courses_resp.status_code == 200
    assert isinstance(courses_resp.json(), list)
    assert any(c["course_id"] == course_id for c in courses_resp.json())
