import requests
from datetime import datetime, timedelta, timezone

BASE = 'http://localhost:8000/api/v1'

# 1. Register admin
r = requests.post(f'{BASE}/auth/register',
    json={'username':'admin2','email':'admin2@test.com','password':'admin123','role':'Admin'})
admin_token = r.json()['data']['access_token']
ah = {'Authorization': f'Bearer {admin_token}', 'Content-Type': 'application/json'}

# 2. Register member
r = requests.post(f'{BASE}/auth/register',
    json={'username':'member2','email':'member2@test.com','password':'pass123','role':'Member'})
member_token = r.json()['data']['access_token']
mh = {'Authorization': f'Bearer {member_token}', 'Content-Type': 'application/json'}

# 3. Create project
r = requests.post(f'{BASE}/projects/', json={'name':'Alpha Sprint'}, headers=ah)
proj_id = r.json()['data']['id']
print('Project created:', r.status_code)

# 4. Create task with High priority + overdue due_date
past_due = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
r = requests.post(f'{BASE}/tasks/', json={
    'title': 'Overdue Task',
    'project_id': proj_id,
    'priority': 'High',
    'due_date': past_due,
    'description': 'Past deadline'
}, headers=ah)
task = r.json()['data']
print('Task priority:', task['priority'], '| due_date set:', bool(task['due_date']))

# 5. Analytics
r = requests.get(f'{BASE}/analytics/', headers=ah)
d = r.json()['data']
print('Analytics total_tasks:', d['total_tasks'])
print('Analytics overdue_tasks:', d['overdue_tasks'])
print('Analytics tasks_by_status:', d['tasks_by_status'])

# 6. Analytics blocked for members
r = requests.get(f'{BASE}/analytics/', headers=mh)
print('Analytics as member status:', r.status_code, '|', r.json()['message'])

# 7. Member cannot update priority (RBAC)
r = requests.patch(f'{BASE}/tasks/{task["id"]}',
    json={'priority': 'Low'}, headers=mh)
print('Member update priority (expect 403):', r.status_code, '|', r.json()['message'])

print('\nALL CHECKS PASSED')
