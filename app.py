"""Flask backend with SQLAlchemy ORM, Argon2 hashing, and migration support."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from uuid import uuid4

from argon2 import PasswordHasher
from flask import Flask, jsonify, request, send_from_directory
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError


app = Flask(__name__, static_folder='static')


def _resolve_database_uri() -> str:
    # Allow DATABASE_URL / DATABASE env to override default sqlite path.
    env_url = os.environ.get('DATABASE_URL') or os.environ.get('DATABASE')
    if env_url:
        if '://' in env_url:
            return env_url
        return f'sqlite:///{env_url}'
    default_path = os.path.join(os.path.dirname(__file__), 'registrations.db')
    return f'sqlite:///{default_path}'


app.config.setdefault('SQLALCHEMY_DATABASE_URI', _resolve_database_uri())
app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)
if not app.config.get('SECRET_KEY'):
    app.config['SECRET_KEY'] = (
        os.environ.get('FLASK_SECRET_KEY')
        or os.environ.get('SECRET_KEY')
        or 'change-me-in-production'
    )

app.secret_key = app.config['SECRET_KEY']

db = SQLAlchemy(app)
migrate = Migrate(app, db)
password_hasher = PasswordHasher()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True)
    timestamp = db.Column(db.String(64), nullable=False)
    fullName = db.Column(db.String(200), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(300), nullable=False)
    role = db.Column(db.String(80))
    bio = db.Column(db.Text)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'fullName': self.fullName,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'bio': self.bio,
        }


class ProgressUpdate(db.Model):
    __tablename__ = 'progress_updates'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.String(64), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(32), nullable=False, default='in-progress')
    blockers = db.Column(db.Text)
    errors = db.Column(db.Text)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'created_at': self.created_at,
            'username': self.username,
            'title': self.title,
            'summary': self.summary,
            'status': self.status,
            'blockers': self.blockers or '',
            'errors': self.errors or '',
        }


class Doubt(db.Model):
    __tablename__ = 'doubts'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.String(64), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    question = db.Column(db.Text, nullable=False)
    resolved = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'created_at': self.created_at,
            'username': self.username,
            'topic': self.topic,
            'question': self.question,
            'resolved': self.resolved,
        }


def init_db() -> None:
    """Create all tables (for developer convenience)."""
    with app.app_context():
        db.create_all()


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/dashboard')
def dashboard():
    return send_from_directory('.', 'dashboard.html')


@app.route('/sitemap.xml')
def sitemap():
    return send_from_directory('static', 'sitemap.xml', mimetype='application/xml')


@app.route('/api/register', methods=['POST'])
def register():
    payload = request.get_json(silent=True)
    if not payload:
        return jsonify(success=False, error='Invalid JSON'), 400

    full = (payload.get('fullName') or '').strip()
    username = (payload.get('username') or '').strip()
    email = (payload.get('email') or '').strip()
    password = payload.get('password') or ''

    if not full or not username or not email or len(password) < 6:
        return jsonify(success=False, error='Missing/invalid fields'), 400

    now = datetime.now(timezone.utc).isoformat()
    rid = f"fut-{uuid4().hex[:10]}"

    try:
        hashed_pw = password_hasher.hash(password)
        user = User(
            id=rid,
            timestamp=now,
            fullName=full,
            username=username,
            email=email,
            password_hash=hashed_pw,
            role=payload.get('role', ''),
            bio=payload.get('bio', ''),
        )
        db.session.add(user)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify(success=False, error='Username or email already exists'), 400
    except Exception:
        db.session.rollback()
        return jsonify(success=False, error='Could not save registration'), 500

    return jsonify(success=True, id=rid)


@app.get('/api/progress')
def get_progress():
    entries = ProgressUpdate.query.order_by(ProgressUpdate.created_at.desc()).all()
    stats = {
        'total': len(entries),
        'withIssues': sum(1 for item in entries if item.errors),
        'statusCounts': {}
    }
    for item in entries:
        stats['statusCounts'][item.status] = stats['statusCounts'].get(item.status, 0) + 1
    return jsonify(success=True, items=[entry.to_dict() for entry in entries], stats=stats)


@app.post('/api/progress')
def create_progress():
    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip()
    title = (payload.get('title') or '').strip()
    summary = (payload.get('summary') or '').strip()
    status = (payload.get('status') or 'in-progress').strip().lower()
    blockers = (payload.get('blockers') or '').strip()
    errors = (payload.get('errors') or '').strip()

    allowed_status = {'in-progress', 'needs-review', 'blocked', 'complete'}
    if status not in allowed_status:
        status = 'in-progress'

    if not username or not title or not summary:
        return jsonify(success=False, error='Missing required fields'), 400

    created_at = datetime.now(timezone.utc).isoformat()

    try:
        entry = ProgressUpdate(
            created_at=created_at,
            username=username,
            title=title,
            summary=summary,
            status=status,
            blockers=blockers,
            errors=errors,
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify(success=True, item=entry.to_dict())
    except Exception:
        db.session.rollback()
        return jsonify(success=False, error='Could not save progress update'), 500


@app.get('/api/doubts')
def get_doubts():
    entries = Doubt.query.order_by(Doubt.created_at.desc()).all()
    return jsonify(success=True, items=[entry.to_dict() for entry in entries])


@app.post('/api/doubts')
def create_doubt():
    payload = request.get_json(silent=True) or {}
    username = (payload.get('username') or '').strip()
    topic = (payload.get('topic') or '').strip()
    question = (payload.get('question') or '').strip()

    if not username or not topic or not question:
        return jsonify(success=False, error='Missing required fields'), 400

    created_at = datetime.now(timezone.utc).isoformat()

    try:
        entry = Doubt(
            created_at=created_at,
            username=username,
            topic=topic,
            question=question,
            resolved=False,
        )
        db.session.add(entry)
        db.session.commit()
        return jsonify(success=True, item=entry.to_dict())
    except Exception:
        db.session.rollback()
        return jsonify(success=False, error='Could not submit question'), 500


if __name__ == '__main__':
    init_db()
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', '5000'))
    app.run(host=host, port=port, debug=debug)
