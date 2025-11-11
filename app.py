"""AuraLog backend with AI-assisted project collaboration."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List
from urllib import request as urlrequest
from urllib.error import URLError, HTTPError
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


ALLOWED_THEMES = {'default', 'dark', 'neon', 'aurora', 'void', 'sunset'}
ALLOWED_CODE_THEMES = {'monokai', 'github', 'dracula'}
ALLOWED_PROJECT_VISIBILITY = {'public', 'private', 'unlisted'}


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
    avatar = db.Column(db.String(400))
    github = db.Column(db.String(300))
    linkedin = db.Column(db.String(300))
    website = db.Column(db.String(400))
    public_profile = db.Column(db.Boolean, nullable=False, default=True)
    email_visible = db.Column(db.Boolean, nullable=False, default=False)
    theme = db.Column(db.String(64), nullable=True)
    code_theme = db.Column(db.String(64), nullable=True)
    notifications = db.Column(db.Text, nullable=True)
    deleted = db.Column(db.Boolean, nullable=False, default=False)
    photos_json = db.Column(db.Text, nullable=True)

    def to_dict(self) -> dict:
        try:
            notifications = json.loads(self.notifications) if self.notifications else {}
            if not isinstance(notifications, dict):
                notifications = {}
        except (TypeError, ValueError):
            notifications = {}
        try:
            photos = json.loads(self.photos_json) if self.photos_json else []
            if not isinstance(photos, list):
                photos = []
            else:
                photos = [str(item) for item in photos if str(item).strip()]
        except (TypeError, ValueError):
            photos = []
        return {
            'id': self.id,
            'timestamp': self.timestamp,
            'fullName': self.fullName,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'bio': self.bio,
            'avatar': self.avatar,
            'github': self.github,
            'linkedin': self.linkedin,
            'website': self.website,
            'public_profile': bool(self.public_profile),
            'email_visible': bool(self.email_visible),
            'theme': self.theme,
            'code_theme': self.code_theme,
            'notifications': notifications,
            'deleted': bool(self.deleted),
            'photos': photos,
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


class DoubtResponse(db.Model):
    __tablename__ = 'doubt_responses'

    id = db.Column(db.Integer, primary_key=True)
    doubt_id = db.Column(db.Integer, db.ForeignKey('doubts.id'), nullable=False)
    created_at = db.Column(db.String(64), nullable=False)
    responder = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_ai = db.Column(db.Boolean, default=False, nullable=False)

    doubt = db.relationship('Doubt', backref=db.backref('responses', lazy='joined', cascade='all, delete-orphan'))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'doubt_id': self.doubt_id,
            'created_at': self.created_at,
            'responder': self.responder,
            'message': self.message,
            'is_ai': self.is_ai,
        }


class Project(db.Model):
    __tablename__ = 'projects'

    id = db.Column(db.String(36), primary_key=True)
    created_at = db.Column(db.String(64), nullable=False)
    updated_at = db.Column(db.String(64), nullable=False)
    owner = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(280), nullable=True)
    description = db.Column(db.Text, nullable=False)
    repo_url = db.Column(db.String(400), nullable=True)
    tags = db.Column(db.Text, nullable=True)
    ai_summary = db.Column(db.Text, nullable=True)
    visibility = db.Column(db.String(32), nullable=False, default='public')
    metadata_json = db.Column('metadata', db.Text, nullable=True)

    @property
    def metadata_dict(self) -> Dict[str, Any]:
        try:
            metadata = json.loads(self.metadata_json) if self.metadata_json else {}
            if not isinstance(metadata, dict):
                return {}
            return metadata
        except (TypeError, ValueError):
            return {}

    def to_dict(self) -> dict:
        metadata = self.metadata_dict
        return {
            'id': self.id,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'owner': self.owner,
            'title': self.title,
            'summary': self.summary,
            'description': self.description,
            'repo_url': self.repo_url,
            'tags': json.loads(self.tags) if self.tags else [],
            'ai_summary': self.ai_summary,
            'visibility': self.visibility or 'public',
            'metadata': metadata,
            'snippets': [snippet.to_dict() for snippet in getattr(self, 'snippets', [])],
        }


class ProjectSnippet(db.Model):
    __tablename__ = 'project_snippets'

    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
    language = db.Column(db.String(64), nullable=True)
    title = db.Column(db.String(200), nullable=True)
    code = db.Column(db.Text, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.String(64), nullable=False)

    project = db.relationship('Project', backref=db.backref('snippets', lazy='joined', cascade='all, delete-orphan'))

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'project_id': self.project_id,
            'language': self.language,
            'title': self.title,
            'code': self.code,
            'notes': self.notes,
            'created_at': self.created_at,
        }


def init_db() -> None:
    """Create all tables (for developer convenience)."""
    with app.app_context():
        db.create_all()


def _call_openai(prompt: str) -> str | None:
    api_key = os.environ.get('AURALOG_OPENAI_API_KEY')
    if not api_key:
        return None

    model = os.environ.get('AURALOG_OPENAI_MODEL', 'gpt-4o-mini')
    payload = json.dumps({
        'model': model,
        'input': prompt,
    }).encode('utf-8')

    req = urlrequest.Request(
        'https://api.openai.com/v1/responses',
        data=payload,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    try:
        with urlrequest.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            output = data.get('output') or data.get('choices')
            if isinstance(output, list) and output:
                # Response schema may differ depending on endpoint
                item = output[0]
                if isinstance(item, dict):
                    return item.get('content') or item.get('text')
                if isinstance(item, str):
                    return item
            if isinstance(data, dict):
                return data.get('content') or data.get('text')
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        app.logger.warning('OpenAI request failed: %s', exc)
    return None


def extract_keywords(text: str, limit: int = 10) -> List[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9_#+-]{2,}", text.lower())
    stopwords = {
        'the', 'and', 'this', 'that', 'with', 'have', 'from', 'there', 'about',
        'your', 'project', 'code', 'into', 'using', 'when', 'also', 'into', 'does',
    }
    freq: dict[str, int] = {}
    for word in words:
        if word in stopwords:
            continue
        freq[word] = freq.get(word, 0) + 1
    ranked = sorted(freq.items(), key=lambda item: item[1], reverse=True)
    return [word for word, _count in ranked[:limit]]


def generate_project_summary(title: str, description: str, code: str | None) -> tuple[str, List[str]]:
    base_text = f"Title: {title}\nDescription: {description}\nCode:\n{code}\n" if code else f"Title: {title}\nDescription: {description}"
    ai_result = _call_openai(
        "Summarise this coding project in 2 sentences and list up to five bullet keywords: " + base_text
    )
    if ai_result:
        extracted_tags = extract_keywords(ai_result)
        return ai_result.strip(), extracted_tags

    short_desc = description.strip().split('\n')[0][:220]
    summary = f"{title.strip()}: {short_desc}" if short_desc else title.strip()
    fallback_tags = extract_keywords(description + '\n' + (code or ''))
    return summary, fallback_tags


def _parse_iso8601(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    text_value = str(value)
    try:
        return datetime.fromisoformat(text_value)
    except ValueError:
        if text_value.endswith('Z'):
            try:
                return datetime.fromisoformat(text_value[:-1] + '+00:00')
            except ValueError:
                return None
        return None


def _build_focus_area(progress_counts: Counter, progress_total: int, blocked: int, needs_review: int,
                      open_doubts: int, resolved_doubts: int, completion_ratio: float, momentum_score: float) -> Dict[str, Any]:
    actions: List[str] = []
    headline = 'Steady momentum detected'
    detail = 'Keep cadence steady and continue logging progress to maintain visibility.'

    if blocked and blocked >= max(1, int(progress_total * 0.25)):
        headline = 'Unblock critical missions'
        detail = 'Multiple updates report blockers. Run a triage huddle to pair mentors with stuck makers.'
        actions = [
            'Identify the top blockers and assign an owner for each within the next stand-up.',
            'Schedule focused support sessions for the teams reporting blockers.',
        ]
    elif open_doubts > resolved_doubts:
        headline = 'Accelerate doubt responses'
        detail = 'Open questions are outnumbering resolved ones. Prioritise feedback loops and mentor responses.'
        actions = [
            'Allocate response slots for mentors to clear the pending doubts queue.',
            'Tag recurring topics and turn them into quick-reference guides.',
        ]
    elif completion_ratio >= 0.6 and momentum_score >= progress_total * 0.5:
        headline = 'Scale what works'
        detail = 'Completion rate is strong. Double down on sharing wins and reusable snippets.'
        actions = [
            'Highlight recent completions in the next mission broadcast.',
            'Encourage teams to convert finished work into playbooks or templates.',
        ]
    elif needs_review > (progress_total - needs_review) and progress_total:
        headline = 'Triage review backlog'
        detail = 'Most updates are waiting for review. Rebalance mentor load to clear the queue.'
        actions = [
            'Rotate reviewers or schedule a review-a-thon to drain the queue.',
            'Document review criteria so feedback stays consistent and faster.',
        ]

    return {
        'headline': headline,
        'detail': detail,
        'actions': actions,
    }


def _compute_mission_insights() -> Dict[str, Any]:
    now = datetime.now(timezone.utc)

    progress_entries = ProgressUpdate.query.order_by(ProgressUpdate.created_at.desc()).all()
    progress_counts = Counter(entry.status for entry in progress_entries)
    progress_total = len(progress_entries)
    blocked = progress_counts.get('blocked', 0)
    needs_review = progress_counts.get('needs-review', 0)
    complete = progress_counts.get('complete', 0)
    in_progress = progress_counts.get('in-progress', 0)

    ages_hours: List[float] = []
    velocity_24h = 0
    velocity_7d = 0
    timeline: List[Dict[str, Any]] = []
    horizon_24h = now - timedelta(hours=24)
    horizon_7d = now - timedelta(days=7)

    for entry in progress_entries:
        stamp = _parse_iso8601(entry.created_at)
        if stamp is not None:
            diff = now - stamp
            ages_hours.append(max(diff.total_seconds() / 3600.0, 0.0))
            if stamp >= horizon_24h:
                velocity_24h += 1
            if stamp >= horizon_7d:
                velocity_7d += 1
        if len(timeline) < 6:
            timeline.append({
                'id': entry.id,
                'title': entry.title,
                'status': entry.status,
                'created_at': entry.created_at,
                'username': entry.username,
            })

    average_age = round(sum(ages_hours) / len(ages_hours), 2) if ages_hours else 0.0
    completion_ratio = round(complete / progress_total, 2) if progress_total else 0.0
    momentum_score = round(
        max(
            (complete * 1.3 + in_progress * 0.9 + velocity_7d * 0.6 + velocity_24h * 0.4)
            - (blocked * 1.4 + needs_review * 0.9),
            0.0,
        ),
        2,
    )

    doubts = Doubt.query.order_by(Doubt.created_at.desc()).all()
    total_doubts = len(doubts)
    open_doubts = sum(1 for item in doubts if not item.resolved)
    resolved_doubts = total_doubts - open_doubts
    resolution_rate = round(resolved_doubts / total_doubts, 2) if total_doubts else 0.0

    projects = Project.query.order_by(Project.created_at.desc()).all()
    visibility_counts = Counter((project.visibility or 'public') for project in projects)
    total_snippets = sum(len(getattr(project, 'snippets', []) or []) for project in projects)

    tag_counter: Counter[str] = Counter()
    for project in projects:
        tags: List[str] = []
        if project.tags:
            try:
                parsed = json.loads(project.tags)
                if isinstance(parsed, list):
                    tags = [str(item).strip().lower() for item in parsed if str(item).strip()]
                elif isinstance(parsed, str):
                    tags = [frag.strip().lower() for frag in parsed.split(',') if frag.strip()]
            except ValueError:
                tags = [frag.strip().lower() for frag in project.tags.split(',') if frag.strip()]
        for tag in tags:
            tag_counter[tag] += 1

    top_tags = [{'tag': tag, 'count': count} for tag, count in tag_counter.most_common(6)]
    recent_projects = [
        {
            'title': project.title,
            'owner': project.owner,
            'created_at': project.created_at,
            'visibility': project.visibility or 'public',
        }
        for project in projects[:5]
    ]

    focus = _build_focus_area(
        progress_counts,
        progress_total,
        blocked,
        needs_review,
        open_doubts,
        resolved_doubts,
        completion_ratio,
        momentum_score,
    )

    metrics_digest = (
        f"Progress total {progress_total} (complete {complete}, blocked {blocked}, needs review {needs_review}). "
        f"Velocity 7d {velocity_7d}, last 24h {velocity_24h}. "
        f"Doubts open {open_doubts} of {total_doubts}. "
        f"Projects {len(projects)} with {total_snippets} snippets. "
        f"Top tags: {', '.join(tag['tag'] for tag in top_tags[:3]) or 'none'}."
    )

    ai_recommendation = _call_openai(
        "You are AuraLog's mission strategist. Given these metrics, propose one actionable recommendation (max 2 sentences) "
        "balancing delivery velocity and code quality."
        f"\nMetrics: {metrics_digest}\nFocus: {focus['headline']} — {focus['detail']}"
    )

    fallback_recommendation = (
        ' • '.join(focus['actions'])
        if focus['actions']
        else focus['detail']
    )

    return {
        'generated_at': now.isoformat(),
        'summary': {
            'progress_total': progress_total,
            'progress_blocked': blocked,
            'progress_needs_review': needs_review,
            'progress_complete': complete,
            'progress_in_progress': in_progress,
            'velocity': {'last_24h': velocity_24h, 'last_7d': velocity_7d},
            'average_age_hours': average_age,
            'completion_ratio': completion_ratio,
            'momentum_score': momentum_score,
        },
        'doubts': {
            'total': total_doubts,
            'open': open_doubts,
            'resolved': resolved_doubts,
            'resolution_rate': resolution_rate,
        },
        'projects': {
            'total': len(projects),
            'visibility': visibility_counts,
            'recent': recent_projects,
            'snippet_count': total_snippets,
            'tag_leaders': top_tags,
        },
        'focus': focus,
        'timeline': timeline,
        'recommendation': ai_recommendation.strip() if ai_recommendation else fallback_recommendation,
        'trending': [tag['tag'] for tag in top_tags[:5]],
        'hybrid_model': 'heuristics+optional-openai',
    }


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
            theme='default',
            code_theme='monokai',
            public_profile=True,
            email_visible=False,
            notifications=json.dumps({'progress': True, 'doubts': True, 'projects': True}),
            photos_json=json.dumps([]),
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


@app.get('/api/profile/<string:username>')
def get_profile(username: str):
    user = User.query.filter_by(username=username, deleted=False).first()
    if user is None:
        return jsonify(success=False, error='User not found'), 404

    token = request.args.get('token') or request.headers.get('X-Auralog-Token')
    if not token and request.headers.get('Authorization', '').startswith('Token '):
        token = request.headers.get('Authorization', '').split(' ', 1)[1].strip()

    is_owner = token == user.id

    # Respect public profile flag unless owner is requesting
    if not user.public_profile and not is_owner:
        return jsonify(success=False, error='Profile is private'), 403

    data = user.to_dict()
    # redact sensitive details for public views
    if not is_owner and not user.email_visible:
        data['email'] = None
    if not is_owner:
        data.pop('notifications', None)
        data.pop('deleted', None)
    # never expose password hash
    data.pop('password_hash', None)
    return jsonify(success=True, profile=data)


@app.post('/api/profile/<string:username>')
def update_profile(username: str):
    payload = request.get_json(silent=True) or {}
    token = payload.get('token') or ''
    updates = payload.get('updates') or {}

    user = User.query.filter_by(username=username, deleted=False).first()
    if user is None:
        return jsonify(success=False, error='User not found'), 404

    # Simple owner check: require token equal to user.id (returned at registration)
    if not token or token != user.id:
        return jsonify(success=False, error='Unauthorized'), 403

    # allow a small set of fields to be updated
    allowed = {
        'fullName', 'bio', 'avatar', 'github', 'linkedin', 'website',
        'public_profile', 'email_visible', 'theme', 'code_theme', 'notifications', 'photos'
    }
    bool_fields = {'public_profile', 'email_visible'}
    changed = False
    for key, val in updates.items():
        if key in allowed:
            if key in bool_fields:
                setattr(user, key, bool(val))
                changed = True
                continue

            if key == 'notifications':
                notifications_payload: Dict[str, Any]
                if isinstance(val, dict):
                    notifications_payload = {str(k): bool(v) for k, v in val.items()}
                elif isinstance(val, list):
                    notifications_payload = {str(item): True for item in val}
                else:
                    continue
                user.notifications = json.dumps(notifications_payload)
                changed = True
                continue

            if key == 'photos':
                photos_payload: List[str] = []
                if isinstance(val, list):
                    photos_payload = [str(item).strip() for item in val if str(item).strip()]
                elif isinstance(val, str):
                    photos_payload = [frag.strip() for frag in val.split(',') if frag.strip()]
                user.photos_json = json.dumps(photos_payload[:12]) if photos_payload else None
                changed = True
                continue

            if key == 'theme':
                theme_value = str(val).strip().lower() if val is not None else 'default'
                if theme_value not in ALLOWED_THEMES:
                    theme_value = 'default'
                user.theme = theme_value
                changed = True
                continue

            if key == 'code_theme':
                code_theme_value = str(val).strip().lower() if val is not None else 'monokai'
                if code_theme_value not in ALLOWED_CODE_THEMES:
                    code_theme_value = 'monokai'
                user.code_theme = code_theme_value
                changed = True
                continue

            if val is None:
                setattr(user, key, None)
            else:
                text_value = str(val).strip()
                setattr(user, key, text_value or None)
            changed = True

    if not changed:
        return jsonify(success=False, error='No valid fields to update'), 400

    try:
        db.session.add(user)
        db.session.commit()
        data = user.to_dict()
        data.pop('password_hash', None)
        return jsonify(success=True, profile=data)
    except Exception:
        db.session.rollback()
        return jsonify(success=False, error='Could not update profile'), 500


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
    return jsonify(success=True, items=[entry.to_dict() | {'responses': [resp.to_dict() for resp in entry.responses]} for entry in entries])


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


@app.post('/api/doubts/<int:doubt_id>/responses')
def create_doubt_response(doubt_id: int):
    payload = request.get_json(silent=True) or {}
    responder = (payload.get('responder') or '').strip()
    message = (payload.get('message') or '').strip()
    is_ai = bool(payload.get('is_ai'))

    if not responder or not message:
        return jsonify(success=False, error='Missing responder or message'), 400

    doubt = Doubt.query.get(doubt_id)
    if doubt is None:
        return jsonify(success=False, error='Doubt not found'), 404

    created_at = datetime.now(timezone.utc).isoformat()
    resolve_flag = payload.get('resolved')

    try:
        response = DoubtResponse(
            doubt_id=doubt_id,
            created_at=created_at,
            responder=responder,
            message=message,
            is_ai=is_ai,
        )
        db.session.add(response)
        if resolve_flag is None:
            if is_ai:
                doubt.resolved = True
        else:
            doubt.resolved = bool(resolve_flag)
        db.session.add(doubt)
        db.session.commit()
        return jsonify(success=True, item=response.to_dict())
    except Exception:
        db.session.rollback()
        return jsonify(success=False, error='Could not save response'), 500


@app.get('/api/projects')
def list_projects():
    projects = (
        Project.query.filter_by(visibility='public')
        .order_by(Project.created_at.desc())
        .all()
    )
    return jsonify(success=True, items=[project.to_dict() for project in projects])


@app.post('/api/projects')
def create_project():
    payload = request.get_json(silent=True) or {}
    title = (payload.get('title') or '').strip()
    description = (payload.get('description') or '').strip()
    owner = (payload.get('owner') or '').strip() or 'anonymous'
    summary = (payload.get('summary') or '').strip()
    repo_url = (payload.get('repo_url') or '').strip()
    code = payload.get('code') or ''
    language = (payload.get('language') or '').strip() or None
    snippet_title = (payload.get('snippet_title') or '').strip() or None
    snippet_notes = (payload.get('snippet_notes') or '').strip() or None
    provided_tags = payload.get('tags')
    visibility = (payload.get('visibility') or 'public').strip().lower()
    metadata_payload = payload.get('metadata')

    if not title or not description:
        return jsonify(success=False, error='Title and description are required'), 400

    now = datetime.now(timezone.utc).isoformat()
    pid = f"proj-{uuid4().hex[:10]}"

    if visibility not in ALLOWED_PROJECT_VISIBILITY:
        visibility = 'public'

    try:
        ai_summary, ai_tags = generate_project_summary(title, description, code)
    except Exception as exc:
        app.logger.warning('Failed to generate AI summary: %s', exc)
        ai_summary, ai_tags = summary or '', []

    tags: List[str]
    if isinstance(provided_tags, list):
        tags = [str(tag).strip() for tag in provided_tags if str(tag).strip()]
    elif isinstance(provided_tags, str) and provided_tags.strip():
        tags = [tag.strip() for tag in provided_tags.split(',') if tag.strip()]
    else:
        tags = []

    if not tags:
        tags = ai_tags

    metadata_dict: Dict[str, Any] = {}
    if isinstance(metadata_payload, dict):
        metadata_dict = {str(k): v for k, v in metadata_payload.items()}
    elif isinstance(metadata_payload, str) and metadata_payload.strip():
        try:
            loaded = json.loads(metadata_payload)
            if isinstance(loaded, dict):
                metadata_dict = loaded
        except ValueError:
            metadata_dict = {'notes': metadata_payload.strip()}

    if repo_url and 'repo_url' not in metadata_dict:
        metadata_dict['repo_url'] = repo_url
    if language and 'primary_language' not in metadata_dict:
        metadata_dict['primary_language'] = language
    metadata_dict.setdefault('snippet_count', 0)

    try:
        project = Project(
            id=pid,
            created_at=now,
            updated_at=now,
            owner=owner,
            title=title,
            summary=summary or ai_summary,
            description=description,
            repo_url=repo_url,
            tags=json.dumps(tags),
            ai_summary=ai_summary,
            visibility=visibility,
            metadata_json=json.dumps(metadata_dict) if metadata_dict else None,
        )
        db.session.add(project)
        db.session.flush()

        if code.strip():
            snippet = ProjectSnippet(
                project_id=pid,
                language=language,
                title=snippet_title,
                code=code,
                notes=snippet_notes,
                created_at=now,
            )
            db.session.add(snippet)

        metadata_dict['snippet_count'] = len(getattr(project, 'snippets', []))
        project.metadata_json = json.dumps(metadata_dict)

        db.session.commit()
        return jsonify(success=True, item=project.to_dict())
    except Exception as exc:
        db.session.rollback()
        app.logger.error('Failed to create project: %s', exc)
        return jsonify(success=False, error='Could not save project'), 500


@app.post('/api/projects/<project_id>/snippets')
def add_project_snippet(project_id: str):
    project = Project.query.get(project_id)
    if project is None:
        return jsonify(success=False, error='Project not found'), 404

    payload = request.get_json(silent=True) or {}
    code = (payload.get('code') or '').strip()
    if not code:
        return jsonify(success=False, error='Code is required'), 400

    language = (payload.get('language') or '').strip() or None
    title = (payload.get('title') or '').strip() or None
    notes = (payload.get('notes') or '').strip() or None
    now = datetime.now(timezone.utc).isoformat()

    try:
        snippet = ProjectSnippet(
            project_id=project_id,
            language=language,
            title=title,
            code=code,
            notes=notes,
            created_at=now,
        )
        db.session.add(snippet)
        project.updated_at = now
        metadata_dict = project.metadata_dict 
        metadata_dict['snippet_count'] = len(getattr(project, 'snippets', []))
        project.metadata_json = json.dumps(metadata_dict)
        db.session.commit()
        return jsonify(success=True, item=snippet.to_dict())
    except Exception as exc:
        db.session.rollback()
        app.logger.error('Failed to add snippet: %s', exc)
        return jsonify(success=False, error='Could not save snippet'), 500


@app.get('/api/insights')
def get_mission_insights():
    try:
        snapshot = _compute_mission_insights()
        return jsonify(success=True, **snapshot)
    except Exception as exc:
        app.logger.error('Failed to compute mission insights: %s', exc)
        return jsonify(success=False, error='Could not generate insights'), 500


if __name__ == '__main__':
    init_db()
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', '5000'))
    app.run(host=host, port=port, debug=debug)
