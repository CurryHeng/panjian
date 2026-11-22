import subprocess
import time

import imageio_ffmpeg
import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(params=[True, False], ids=['audio', 'silent'])
def footage(tmp_path, request):
    path = tmp_path / 'source.mp4'
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), '-y', '-f', 'lavfi', '-i',
           'color=c=red:s=160x120:r=12:d=3', '-f', 'lavfi', '-i',
           'color=c=blue:s=160x120:r=12:d=3']
    if request.param:
        cmd += ['-f', 'lavfi', '-i', 'sine=frequency=440:duration=6']
    cmd += ['-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0[v]',
            '-map', '[v]']
    if request.param:
        cmd += ['-map', '2:a', '-c:a', 'aac']
    cmd += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return path


def upload(client, path):
    with path.open('rb') as stream:
        response = client.post('/api/projects', files={'file': ('比赛.mp4', stream, 'video/mp4')})
    assert response.status_code == 200, response.text
    return response.json()


def test_import_persist_and_reject_invalid_video(tmp_path, footage):
    root = tmp_path / 'data'
    with TestClient(create_app(root)) as client:
        project = upload(client, footage)
        assert project['duration'] == pytest.approx(6, abs=0.2)
        assert project['width'] == 160
        bad = client.post('/api/projects', files={'file': ('bad.mp4', b'not a video', 'video/mp4')})
        assert bad.status_code == 422
    with TestClient(create_app(root)) as client:
        assert client.get('/api/projects').json()[0]['id'] == project['id']


def test_clips_bounds_and_persistence(tmp_path, footage):
    root = tmp_path / 'data'
    with TestClient(create_app(root)) as client:
        project = upload(client, footage)
        url = f"/api/projects/{project['id']}/clips"
        for start, end in [(-1, 2), (2, 2), (4, 9)]:
            assert client.put(url, json={'clips': [{'id': 'a', 'start': start, 'end': end}]}).status_code == 422
        assert client.put(url, content='{"clips":[{"id":"a","start":0,"end":NaN}]}', headers={'Content-Type': 'application/json'}).status_code == 422
        clips = [{'id': 'b', 'start': 3.5, 'end': 5, 'title': '回合', 'notes': '待校准'}]
        assert client.put(url, json={'clips': clips}).status_code == 200
    with TestClient(create_app(root)) as client:
        saved = client.get(f"/api/projects/{project['id']}").json()
        assert saved['clips'] == clips


def test_export_order_duration_and_errors(tmp_path, footage, request):
    with TestClient(create_app(tmp_path / 'data')) as client:
        project = upload(client, footage)
        pid = project['id']
        assert client.post(f'/api/projects/{pid}/exports').status_code == 422
        clips = [{'id': 'blue', 'start': 3.5, 'end': 5}, {'id': 'red', 'start': 0.5, 'end': 1.5}]
        assert client.put(f'/api/projects/{pid}/clips', json={'clips': clips}).status_code == 200
        job = client.post(f'/api/projects/{pid}/exports').json()
        for _ in range(100):
            job = client.get(f"/api/jobs/{job['id']}").json()
            if job['status'] in ('completed', 'failed'):
                break
            time.sleep(0.1)
        assert job['status'] == 'completed', job
        response = client.get(f"/api/exports/{job['id']}")
        assert response.status_code == 200
        output = tmp_path / 'result.mp4'
        output.write_bytes(response.content)
        reader = imageio_ffmpeg.read_frames(str(output), pix_fmt='rgb24')
        metadata = next(reader)
        frame = next(reader)
        reader.close()
        assert metadata['duration'] == pytest.approx(2.5, abs=0.25)
        assert bool(metadata.get('audio_codec')) == request.node.callspec.params['footage']
        assert frame[2] > frame[0] + 100, 'Export must start with blue clip, not source order'
        assert client.get('/api/projects/unknown').status_code == 404
        assert client.get('/api/exports/unknown').status_code == 404


def test_cross_origin_write_rejected(tmp_path):
    with TestClient(create_app(tmp_path / 'data')) as client:
        response = client.post('/api/projects', headers={'Origin': 'https://example.com'})
        assert response.status_code == 403


def test_automatic_upload_with_no_players(tmp_path, footage):
    with TestClient(create_app(tmp_path / 'data')) as client:
        with footage.open('rb') as stream:
            project = client.post('/api/projects?auto=true', files={'file': ('sample.mp4', stream)}).json()
        for _ in range(100):
            job = client.get(f"/api/projects/{project['id']}/exports").json()[0]
            if job['status'] not in ('queued', 'running'):
                break
            time.sleep(0.1)
        assert job['status'] == 'completed', job
        assert 'download_url' in job
        clips = client.get(f"/api/projects/{project['id']}").json()['clips']
        assert len(clips) == 1
        assert clips[0]['start'] == 0
        assert clips[0]['end'] == project['duration']
        assert '非精彩识别结论' in clips[0]['notes']
