"""Rank time windows from local video frames, without reading review annotations."""
from functools import lru_cache
from pathlib import Path
import subprocess
import uuid
import os
from app.backtrack import apply_backtrack

import imageio_ffmpeg
import numpy as np
import onnxruntime as ort


class NoHighlights(Exception):
    pass


@lru_cache(maxsize=1)
def detector():
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.log_severity_level = 3
    model = Path(__file__).parent / 'models' / 'nanodet.onnx'
    return ort.InferenceSession(str(model), options, providers=['CPUExecutionProvider'])


def frame_scores(source):
    network = detector()
    class_outputs = [item.name for item in network.get_outputs() if item.shape[-1] == 80]
    mean = np.array([103.53, 116.28, 123.675], dtype=np.float32)
    std = np.array([57.375, 57.12, 58.395], dtype=np.float32)
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-loglevel', 'error', '-i', str(source),
               '-an', '-vf', 'fps=2,scale=416:416:force_original_aspect_ratio=decrease,pad=416:416:(ow-iw)/2:(oh-ih)/2',
               '-pix_fmt', 'rgb24', '-f', 'rawvideo', '-']
    previous = None
    scores = []
    size = 416 * 416 * 3
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as process:
        try:
            while data := process.stdout.read(size):
                frame = np.frombuffer(data, dtype=np.uint8).reshape(416, 416, 3)
                tensor = ((frame - mean) / std).transpose(2, 0, 1)[None]
                outputs = network.run(class_outputs, {network.get_inputs()[0].name: tensor})
                person = max(float(output[0, :, 0].max()) for output in outputs)
                small = frame[::8, ::8].astype(np.int16)
                movement = 0 if previous is None else np.abs(small - previous).mean()
                previous = small
                scores.append((person, movement, person * (0.25 + min(movement / 30, 1))))
        finally:
            process.stdout.close()
        if process.wait():
            raise ValueError('视频抽帧失败')
    return scores


def build_plan(source, duration):
    return plan_from_scores(frame_scores(source), duration, backtrack_enabled=os.environ.get('PANJIAN_START_BACKTRACK', '1') != '0')


def plan_from_scores(frames, duration, backtrack_enabled=True):
    width = min(12, len(frames))  # Six seconds at two samples per second.
    windows = []
    for index in range(len(frames) - width + 1) if width else ():
        section = frames[index:index + width]
        if max(p for p, _, _ in section) < 0.35 or np.mean([m for _, m, _ in section]) < 1:
            continue
        start = index / 2
        end = min(duration, start + width / 2)
        if end > start:
            windows.append((float(np.mean([s for _, _, s in section])), start, end))
    if not np.isfinite(duration) or duration <= 0:
        raise ValueError('视频时长必须为正数')
    selected = []
    limit = min(6, max(1, round(duration / 15)))
    best = max(windows)[0] if windows else 0
    for score, start, end in sorted(windows, reverse=True):
        if score < 0.7 * best:
            break
        if all(end <= a or start >= b for a, b in selected):
            selected.append((start, end))
        if len(selected) >= limit:
            break
    candidates = [dict(start=s, end=e) for s, e in sorted(selected)]
    tail = dict(start=max(0, duration - 10), end=duration,
                reason='recording_habit_tail', semantic_event_verified=False)
    intervals = [(max(0, s - 2), min(duration, e + 2), 'model')
                 for s, e in selected]
    intervals.append((tail['start'], tail['end'], 'recording_habit_tail'))
    merged = []
    for start, end, reason in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
            merged[-1][2].add(reason)
        else:
            merged.append([start, end, {reason}])
    clips = []
    provenance = []
    for i, (start, end, reasons) in enumerate(merged, 1):
        notes = []
        if 'model' in reasons:
            notes.append('人物与运动量推荐，前后各留至多2秒')
        if 'recording_habit_tail' in reasons:
            notes.append('含原片末尾10秒（不足10秒取全片），按拍摄习惯保留，非精彩识别结论')
        clip = dict(id=uuid.uuid4().hex, start=start, end=end,
                    title=f'片段 {i}', notes='；'.join(notes))
        clips.append(clip)
        provenance.append(dict(clip_id=clip['id'], reasons=sorted(reasons)))
    plan = dict(schema_version=2, strategy='person_motion_windows_v3_tail',
                source_duration=duration, sample_fps=2,
                padding_before=2, padding_after=2, candidates=candidates,
                tail_preservation=tail, clip_provenance=provenance,
                recommendation_status='model_and_tail' if selected else 'tail_only',
                clips=clips, semantic_event_verified=False,
                boundary_policy='clamp_then_merge_overlaps_chronologically')
    return apply_backtrack(plan, frames, enabled=backtrack_enabled)



def recommend(source, duration):
    return build_plan(source, duration)['clips']
