"""Local FFmpeg operations; source footage is never modified."""
import math
import subprocess
from pathlib import Path

import imageio_ffmpeg


def run_ffmpeg(arguments, timeout=1800):
    command = [imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-hide_banner', *map(str, arguments)]
    result = subprocess.run(command, capture_output=True, timeout=timeout,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if result.returncode:
        raise ValueError('视频处理失败：格式不受支持、素材损坏或编码器无法处理。')


def probe(path):
    reader = imageio_ffmpeg.read_frames(str(path))
    try:
        metadata = next(reader)
        duration = float(metadata.get('duration', 0))
        width, height = metadata['size']
        if not math.isfinite(duration) or duration <= 0 or width <= 0 or height <= 0:
            raise ValueError('视频时长或尺寸无效')
        return {'duration': duration, 'width': width, 'height': height}
    except Exception as exc:
        raise ValueError('无法读取视频，请使用完整、可播放的 MP4/MOV/WebM 文件。') from exc
    finally:
        reader.close()


def export_clips(source, clips, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    parts = []
    for index, clip in enumerate(clips):
        part = directory / f'part-{index:04d}.mp4'
        run_ffmpeg(['-y', '-ss', clip['start'], '-i', source,
                    '-t', clip['end'] - clip['start'], '-map', '0:v:0', '-map', '0:a:0?',
                    '-vf', 'scale=trunc(iw/2)*2:trunc(ih/2)*2,setsar=1',
                    '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '21',
                    '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-ar', '48000',
                    '-avoid_negative_ts', 'make_zero', part])
        parts.append(part)
    # Only generated, fixed ASCII names appear in the concat file.
    manifest = directory / 'concat.txt'
    manifest.write_text('\n'.join(f"file '{p.name}'" for p in parts), encoding='utf-8')
    output = directory / 'highlight.mp4'
    run_ffmpeg(['-y', '-f', 'concat', '-safe', '1', '-i', manifest,
                '-c', 'copy', '-movflags', '+faststart', output])
    probe(output)
    for part in parts:
        part.unlink(missing_ok=True)
    manifest.unlink(missing_ok=True)
    return output
