import os
import json
import pytest

from app import app, db, User, ProgressUpdate, Doubt, Project, ProjectSnippet, DoubtResponse


@pytest.fixture
def client(tmp_path):
    db_uri = f"sqlite:///{tmp_path / 'test_reg.db'}"
    app.config.update({
        'SQLALCHEMY_DATABASE_URI': db_uri,
        'TESTING': True
    })
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.create_all()
    with app.test_client() as client:
        yield client


def test_register_success(client):
    payload = {
        'fullName': 'Alice Example',
        'username': 'alice123',
        'email': 'alice@example.com',
        'password': 'supersecret',
        'role': 'explorer',
        'bio': 'Hello world'
    }
    rv = client.post('/api/register', json=payload)
    assert rv.status_code == 200
    j = rv.get_json()
    assert j['success'] is True
    assert 'id' in j

    with app.app_context():
        user = User.query.filter_by(username=payload['username']).first()
        assert user is not None
        assert user.username == payload['username']
        assert user.email == payload['email']
        assert user.password_hash != payload['password']
        assert user.theme == 'default'
        assert user.code_theme == 'monokai'
        assert user.public_profile is True
        assert json.loads(user.photos_json) == []


def test_register_missing_fields(client):
    payload = {'fullName': '', 'username': '', 'email': '', 'password': '123'}
    rv = client.post('/api/register', json=payload)
    assert rv.status_code == 400
    j = rv.get_json()
    assert j['success'] is False


def test_progress_workflow(client):
    payload = {
        'username': 'alice123',
        'title': 'Sprint 1',
        'summary': 'Integrated backend with UI',
        'status': 'needs-review',
        'errors': 'Failing unit test in pipeline'
    }
    rv = client.post('/api/progress', json=payload)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True

    rv = client.get('/api/progress')
    assert rv.status_code == 200
    listing = rv.get_json()
    assert listing['success'] is True
    assert listing['stats']['total'] == 1
    assert listing['stats']['withIssues'] == 1
    assert listing['items'][0]['username'] == payload['username']

    with app.app_context():
        assert ProgressUpdate.query.count() == 1


def test_doubt_submission(client):
    payload = {
        'username': 'alice123',
        'topic': 'Deployment',
        'question': 'How do we configure HTTPS on production?'
    }
    rv = client.post('/api/doubts', json=payload)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True

    rv = client.get('/api/doubts')
    assert rv.status_code == 200
    listing = rv.get_json()
    assert listing['success'] is True
    assert len(listing['items']) == 1
    assert listing['items'][0]['topic'] == payload['topic']
    assert listing['items'][0]['responses'] == []

    with app.app_context():
        doubt = Doubt.query.first()
        assert doubt is not None
        assert doubt.resolved is False


def test_doubt_response_flow(client):
    create_payload = {
        'username': 'mentor1',
        'topic': 'API latency',
        'question': 'Why is the response time spiking?'
    }
    rv = client.post('/api/doubts', json=create_payload)
    assert rv.status_code == 200
    doubt_item = rv.get_json()['item']

    response_payload = {
        'responder': 'mentor-team',
        'message': 'Check the database indexes and API pagination.',
        'is_ai': False
    }
    rv = client.post(f"/api/doubts/{doubt_item['id']}/responses", json=response_payload)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    item = data['item']
    assert item['responder'] == response_payload['responder']

    rv = client.get('/api/doubts')
    listing = rv.get_json()
    assert listing['items'][0]['responses']
    assert listing['items'][0]['responses'][0]['message'].startswith('Check the database')

    with app.app_context():
        assert DoubtResponse.query.count() == 1


def test_project_creation_and_listing(client):
    payload = {
        'owner': 'team-nebula',
        'title': 'Quantum IDE',
        'description': 'A browser-based IDE that integrates quantum circuit simulation.',
        'repo_url': 'https://github.com/example/quantum-ide',
        'summary': '',
        'tags': 'python,quantum,simulation',
        'code': 'def simulate():\n    return "ok"',
        'language': 'python',
        'snippet_title': 'Simulator stub',
        'snippet_notes': 'Prototype function'
    }

    rv = client.post('/api/projects', json=payload)
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    project = data['item']
    assert project['title'] == payload['title']
    assert project['ai_summary']
    assert 'python' in project['tags']
    assert project['snippets'][0]['language'] == 'python'
    assert project['visibility'] == 'public'
    assert project['metadata']['snippet_count'] == 1

    rv = client.get('/api/projects')
    listing = rv.get_json()
    assert listing['success'] is True
    assert len(listing['items']) == 1
    assert listing['items'][0]['owner'] == payload['owner']

    private_payload = {
        'owner': 'shadow-team',
        'title': 'Stealth Ops',
        'description': 'Hidden project',
        'visibility': 'private'
    }
    rv = client.post('/api/projects', json=private_payload)
    assert rv.status_code == 200

    rv = client.get('/api/projects')
    listing = rv.get_json()
    assert listing['success'] is True
    assert len(listing['items']) == 1

    with app.app_context():
        assert Project.query.count() == 2
        assert ProjectSnippet.query.count() == 1


def test_profile_update_and_privacy(client):
    register_payload = {
        'fullName': 'Nova Coder',
        'username': 'nova',
        'email': 'nova@example.com',
        'password': 'future-proof',
        'role': 'builder',
        'bio': 'Initial bio'
    }
    rv = client.post('/api/register', json=register_payload)
    assert rv.status_code == 200
    token = rv.get_json()['id']

    updates = {
        'fullName': 'Nova Polaris',
        'bio': 'Building galaxies in code',
        'github': 'https://github.com/nova',
        'public_profile': False,
        'email_visible': False,
        'theme': 'aurora',
        'code_theme': 'dracula',
        'notifications': {
            'progress': True,
            'projects': False,
            'doubts': True
        },
        'photos': [
            'https://images.example.com/nova-card.png',
            'https://images.example.com/nova-lab.png'
        ]
    }

    rv = client.post('/api/profile/nova', json={'token': token, 'updates': updates})
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    profile = data['profile']
    assert profile['theme'] == 'aurora'
    assert profile['notifications']['progress'] is True
    assert profile['public_profile'] is False
    assert profile['photos'][0].endswith('nova-card.png')

    rv = client.get('/api/profile/nova')
    assert rv.status_code == 403

    rv = client.get(f'/api/profile/nova?token={token}')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    profile = data['profile']
    assert profile['email'] == register_payload['email']
    assert profile['notifications']['doubts'] is True
    assert profile['code_theme'] == 'dracula'
    assert len(profile['photos']) == 2

    with app.app_context():
        user = User.query.filter_by(username='nova').first()
        assert user is not None
        assert user.theme == 'aurora'
        assert user.email_visible is False
        assert json.loads(user.photos_json)[1].endswith('nova-lab.png')


def test_mission_insights_endpoint(client):
    # Seed progress updates across statuses
    statuses = ['in-progress', 'blocked', 'needs-review', 'complete']
    for idx, status in enumerate(statuses, start=1):
        payload = {
            'username': f'user{idx}',
            'title': f'Update {idx}',
            'summary': f'Sample summary {idx}',
            'status': status,
            'blockers': 'Env setup' if status == 'blocked' else '',
            'errors': 'Tests failing' if status == 'needs-review' else ''
        }
        rv = client.post('/api/progress', json=payload)
        assert rv.status_code == 200

    # Seed a doubt and resolve it via mentor response
    rv = client.post('/api/doubts', json={
        'username': 'mentor1',
        'topic': 'CI pipeline',
        'question': 'Why is the workflow stuck on lint stage?'
    })
    assert rv.status_code == 200
    doubt_id = rv.get_json()['item']['id']

    rv = client.post(f'/api/doubts/{doubt_id}/responses', json={
        'responder': 'mentor-team',
        'message': 'Re-run with the new cache key; lint config was updated.',
        'is_ai': False,
        'resolved': True
    })
    assert rv.status_code == 200

    # Publish a project with snippet metadata
    project_payload = {
        'owner': 'mission-alpha',
        'title': 'Telemetry Engine',
        'description': 'Streams metrics into the insights engine.',
        'repo_url': 'https://github.com/example/telemetry',
        'summary': 'Real-time metrics capture',
        'tags': 'python,analytics,ai',
        'code': 'def tick():\n    return True',
        'language': 'python',
        'snippet_title': 'Heartbeat loop',
        'snippet_notes': 'Keeps the collector alive'
    }
    rv = client.post('/api/projects', json=project_payload)
    assert rv.status_code == 200

    rv = client.get('/api/insights')
    assert rv.status_code == 200
    data = rv.get_json()
    assert data['success'] is True
    assert data['summary']['progress_total'] >= len(statuses)
    assert data['doubts']['total'] == 1
    assert data['projects']['total'] == 1
    assert isinstance(data['projects']['tag_leaders'], list)
    assert 'recommendation' in data