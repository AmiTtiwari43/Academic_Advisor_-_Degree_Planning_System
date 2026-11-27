import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')
django.setup()

from django.test import Client

client = Client(SERVER_NAME="localhost")

print("=== 1. HEALTH CHECK ENDPOINT ===")
res = client.get('/api/health/')
print(f"Status: {res.status_code}")
print("Payload:", json.dumps(res.json(), indent=2))
assert res.status_code == 200, f"Expected 200, got {res.status_code}"
assert res.json()['status'] == 'ok'
assert 'neon-postgresql (connected)' in res.json()['database']
print("-> Health check passed with active Neon PostgreSQL connection!")

print("\n=== 2. AUTHENTICATION AGAINST NEON POSTGRES ===")
login_res = client.post(
    '/api/auth/login/',
    data={'username': 'admin_super', 'password': 'Password123!'},
    content_type='application/json'
)
print(f"Login status: {login_res.status_code}")
user_data = login_res.json()
print(f"Logged in user: {user_data.get('username')} ({user_data.get('email')})")
print(f"User role: {user_data.get('role')} | Institution: {user_data.get('institution', {}).get('name')}")
assert login_res.status_code == 200
print("-> Authentication against Neon PostgreSQL user tables passed!")

print("\n=== 3. AUTHENTICATED USER ME ENDPOINT ===")
me_res = client.get('/api/auth/me/')
print(f"Me status: {me_res.status_code}")
print(f"Current session user: {me_res.json().get('username')}")
assert me_res.status_code == 200
print("-> Session authentication and cookie retrieval passed!")

print("\n=== 4. QUERY STUDENTS FROM NEON POSTGRES ===")
stu_res = client.get('/api/v1/student-records/')
print(f"Students endpoint status: {stu_res.status_code}")
payload = stu_res.json()
results = payload.get('results', payload) if isinstance(payload, dict) else payload
print(f"Total students fetched from Neon: {len(results)}")
for idx, s in enumerate(results[:3], start=1):
    print(f"  [{idx}] {s.get('student_name', s.get('student_username'))} | Programme: {s.get('programme_name')} | CGPA: {s.get('cgpa')}")
assert stu_res.status_code == 200
assert len(results) > 0
print("-> Relational multi-table querying from Neon passed!")

print("\n=== 5. FRONTEND SPA CATCH-ALL ROUTE ===")
spa_res = client.get('/')
print(f"SPA root status: {spa_res.status_code}")
print(f"Content-Type: {spa_res.get('Content-Type')}")
content = b"".join(spa_res.streaming_content) if spa_res.streaming else spa_res.content
assert b'<div id="root"></div>' in content
print("-> SPA root successfully served compiled frontend bundle!")

print("\n=======================================================")
print(" ALL END-TO-END SERVICES VERIFIED AGAINST NEON POSTGRES ")
print("=======================================================")
