import os
import sqlite3
import json
import pytest

from app import app, db, User, ProgressUpdate, Doubt


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

    with app.app_context():
        doubt = Doubt.query.first()
        assert doubt is not None
        assert doubt.resolved is False