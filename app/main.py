"""Single-user local prototype. Do not expose this server on a network."""
import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.media import export_clips, probe
from app.highlights import build_plan, NoHighlights

BASE = Path(__file__).resolve().parent
MAX_UPLOAD = 2 * 1024 ** 3
logger = logging.getLogger(__name__)


class Clip(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    id: str = Field(min_length=1, max_length=80)
    start: float = Field(ge=0)
    end: float = Field(gt=0)
    title: str = Field(default='', max_length=200)
    notes: str = Field(default='', max_length=4000)


class Selections(BaseModel):
    clips: list[Clip] = Field(max_length=100)


def create_app(data_dir=None):
    root = Path(data_dir or os.environ.get('PANJIAN_DATA', BASE.parent / 'data')).resolve()
    projects = root / 'projects'
    exports = root / 'exports'
    projects.mkdir(parents=True, exist_ok=True)
    exports.mkdir(parents=True, exist_ok=True)
    lock = threading.RLock()
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='panjian-export')

    def read(path):
        if not path.is_file():
            raise HTTPException(404, '找不到项目或任务')
        with lock:
            return json.loads(path.read_text(encoding='utf-8'))

    def write(path, payload):
        with lock:
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(payload, ensure_ascii=False, allow_nan=False), encoding='utf-8')
            temp.replace(path)

    def identifier(value):
        if len(value) != 32 or any(c not in '0123456789abcdef' for c in value):
            raise HTTPException(404, '找不到项目或任务')
        return value

    def project_path(pid):
        return projects / identifier(pid) / 'project.json'

    def job_path(jid):
        return exports / identifier(jid) / 'job.json'

    # A previous process cannot resume encoder subprocesses safely.
    for path in exports.glob('*/job.json'):
        job = read(path)
        if job['status'] in ('queued', 'running'):
            job.update(status='failed', error='服务已重启，请重新导出。')
            write(path, job)

    @asynccontextmanager
    async def lifespan(app):
        yield
        pool.shutdown(wait=True)

    app = FastAPI(title='盘见 · 本地剪辑工作台', lifespan=lifespan)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['127.0.0.1', 'localhost', 'testserver'])

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Pydantic error inputs may contain NaN, which JSON cannot encode.
        return JSONResponse({'detail': '片段参数无效，请检查起止时间、字段长度和片段数量。'}, status_code=422)

    @app.middleware('http')
    async def same_origin(request, call_next):
        origin = request.headers.get('origin')
        if request.method not in ('GET', 'HEAD', 'OPTIONS'):
            if request.headers.get('sec-fetch-site') == 'cross-site':
                return JSONResponse({'detail': '不接受跨站操作'}, status_code=403)
            if origin and urlparse(origin).netloc != request.headers.get('host'):
                return JSONResponse({'detail': '不接受跨站操作'}, status_code=403)
        return await call_next(request)

    @app.get('/api/health')
    def health():
        return {'status': 'ok', 'mode': 'local-auto-highlights'}

    @app.get('/api/projects')
    def list_projects():
        return sorted([read(p) for p in projects.glob('*/project.json')],
                      key=lambda p: p['created_at'], reverse=True)

    @app.post('/api/projects')
    def upload(file: UploadFile, auto: bool = False):
        from datetime import datetime, timezone
        pid = uuid.uuid4().hex
        directory = projects / pid
        directory.mkdir()
        suffix = Path(file.filename or '').suffix.lower()
        if suffix not in ('.mp4', '.mov', '.mkv', '.webm', '.avi', '.m4v'):
            directory.rmdir()
            raise HTTPException(422, '请选择 MP4、MOV、MKV、WebM、AVI 或 M4V 视频')
        source = directory / ('source' + suffix)
        try:
            total = 0
            with source.open('wb') as stream:
                while chunk := file.file.read(1024 * 1024):
                    total += len(chunk)
                    if total > MAX_UPLOAD:
                        raise HTTPException(413, '本地原型单个视频上限为 2 GiB')
                    stream.write(chunk)
            metadata = probe(source)
            project = {'id': pid, 'name': Path(file.filename).name, **metadata,
                       'bytes': total, 'source_name': source.name, 'clips': [],
                       'created_at': datetime.now(timezone.utc).isoformat(),
                       'selection_mode': 'manual'}
            write(directory / 'project.json', project)
            if auto:
                queue_job(project, automatic=True)
            return project
        except (ValueError, HTTPException) as exc:
            source.unlink(missing_ok=True)
            directory.rmdir()
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(422, str(exc)) from exc
        finally:
            file.file.close()

    @app.get('/api/projects/{pid}')
    def get_project(pid: str):
        return read(project_path(pid))

    @app.get('/api/projects/{pid}/source')
    def source_video(pid: str):
        project = read(project_path(pid))
        return FileResponse(project_path(pid).parent / project['source_name'])

    @app.put('/api/projects/{pid}/clips')
    def save_clips(pid: str, selection: Selections):
        with lock:
            path = project_path(pid)
            project = read(path)
            clips = [c.model_dump() for c in selection.clips]
            if len({c['id'] for c in clips}) != len(clips):
                raise HTTPException(422, '片段编号不能重复')
            for clip in clips:
                if clip['start'] >= clip['end'] or clip['end'] > project['duration']:
                    raise HTTPException(422, '片段需满足：0 ≤ 起点 < 终点 ≤ 视频时长')
            project['clips'] = clips
            write(path, project)
            return project

    def perform_export(job, project):
        path = job_path(job['id'])
        try:
            job.update(status='running')
            write(path, job)
            source = project_path(project['id']).parent / project['source_name']
            if job.get('automatic'):
                job.update(stage='analyzing')
                write(path, job)
                plan = build_plan(source, project['duration'])
                write(path.parent / 'edit-plan.json', plan)
                clips = plan['clips']
                with lock:
                    current = read(project_path(project['id']))
                    if not current['clips'] and current['selection_mode'] == 'manual':
                        current.update(clips=clips, selection_mode='automatic')
                        write(project_path(project['id']), current)
                project = dict(project, clips=clips)
            job.update(stage='encoding')
            write(path, job)
            output = export_clips(source,
                                  project['clips'], path.parent)
            job.update(status='completed', bytes=output.stat().st_size,
                       download_url=f"/api/exports/{job['id']}")
        except NoHighlights as exc:
            job.update(status='no_candidates', error=str(exc))
        except Exception:
            logger.exception('Export failed: %s', job['id'])
            job.update(status='failed', error='导出失败，请确认磁盘空间、片段范围及视频可播放性后重试。')
        write(path, job)

    def queue_job(project, automatic=False):
        jid = uuid.uuid4().hex
        (exports / jid).mkdir()
        job = {'id': jid, 'project_id': project['id'], 'status': 'queued', 'error': None, 'automatic': automatic}
        write(job_path(jid), job)
        pool.submit(perform_export, dict(job), project)
        return job

    @app.post('/api/projects/{pid}/exports')
    def start_export(pid: str):
        with lock:
            project = read(project_path(pid))
            if not project['clips']:
                raise HTTPException(422, '请先添加并保存至少一个片段')
            active = [read(p) for p in exports.glob('*/job.json')]
            if any(j['status'] in ('queued', 'running') for j in active):
                raise HTTPException(409, '已有导出任务，请等待完成后再试')
            return queue_job(project)

    @app.get('/api/jobs/{jid}')
    def get_job(jid: str):
        return read(job_path(jid))

    @app.get('/api/projects/{pid}/exports')
    def list_exports(pid: str):
        read(project_path(pid))
        return [j for p in exports.glob('*/job.json') if (j := read(p))['project_id'] == pid]

    @app.get('/api/exports/{jid}')
    def download(jid: str):
        job = read(job_path(jid))
        if job['status'] != 'completed':
            raise HTTPException(409, '视频尚未生成')
        return FileResponse(job_path(jid).parent / 'highlight.mp4', media_type='video/mp4',
                            filename='panjian-highlight.mp4')

    @app.get('/')
    def index():
        return FileResponse(BASE / 'static' / 'index.html')

    app.mount('/static', StaticFiles(directory=BASE / 'static', check_dir=False), name='static')
    return app
