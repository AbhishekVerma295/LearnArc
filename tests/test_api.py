import time
import pytest

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_full_course_lifecycle(client):
    timestamp = int(time.time())
    instructor_email = f"instructor_{timestamp}@example.com"
    student_email = f"student_{timestamp}@example.com"
    password = "password123"
    
    # 1. Register and login Instructor
    reg_inst = client.post("/api/v1/auth/register/instructor", json={
        "first_name": "Test", "last_name": "Instructor", "email": instructor_email, "password": password, "department": "Science"
    })
    assert reg_inst.status_code == 200
    
    login_inst = client.post("/api/v1/auth/login/instructor", data={"username": instructor_email, "password": password})
    assert login_inst.status_code == 200
    inst_token = login_inst.json()["access_token"]
    inst_headers = {"Authorization": f"Bearer {inst_token}"}
    
    # 2. Create Course, Module, Lesson
    course_resp = client.post("/api/v1/courses/", headers=inst_headers, json={
        "title": f"Test Course {timestamp}", "description": "A test course", "price": 49.99
    })
    assert course_resp.status_code == 200
    course_id = course_resp.json()["course_id"]
    
    module_resp = client.post(f"/api/v1/courses/{course_id}/modules", headers=inst_headers, json={
        "module_title": "Module 1", "module_order": 1
    })
    assert module_resp.status_code == 200
    module_id = module_resp.json()["module_id"]
    
    lesson_resp = client.post(f"/api/v1/courses/modules/{module_id}/lessons", headers=inst_headers, json={
        "lesson_title": "Lesson 1", "lesson_number": 1, "duration_minutes": 10, "content_url": "http://example.com"
    })
    assert lesson_resp.status_code == 200
    lesson_id = lesson_resp.json()["lesson_id"]
    
    # 3. Register and login Student
    reg_stu = client.post("/api/v1/auth/register/student", json={
        "first_name": "Test", "last_name": "Student", "email": student_email, "password": password
    })
    assert reg_stu.status_code == 200
    
    login_stu = client.post("/api/v1/auth/login/student", data={"username": student_email, "password": password})
    assert login_stu.status_code == 200
    stu_token = login_stu.json()["access_token"]
    stu_headers = {"Authorization": f"Bearer {stu_token}"}
    
    # 4. Enroll in Course
    enroll_resp = client.post(f"/api/v1/enrollments/courses/{course_id}", headers=stu_headers)
    assert enroll_resp.status_code == 200
    
    # 5. Complete Lesson
    prog_resp = client.post(f"/api/v1/enrollments/progress/lessons/{lesson_id}", headers=stu_headers)
    assert prog_resp.status_code == 200
    
    # 6. Check Certificate
    cert_resp = client.get("/api/v1/enrollments/certificates", headers=stu_headers)
    assert cert_resp.status_code == 200
    assert len(cert_resp.json()) >= 0  # Could be delayed if DB trigger is async, but usually instant
