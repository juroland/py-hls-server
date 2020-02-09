"""
Record from the default microphone in an infinite loop and create
a Live Playlist (Sliding Window).

Reference: https://developer.apple.com/documentation/http_live_streaming/
"""

import hashlib
import os
import multiprocessing

import pyaudio
import pydub

from typing import List, Tuple

MEDIAS_DIR: str = os.environ.get("HLS_SERVER_MEDIAS_DIR", ".")
TARGET_SEGMENT_DURATION: int = int(
    os.environ.get("HLS_SERVER_TARGET_SEGMENT_DURATION", 2)
)


def update_playlist(
    sequence: List[Tuple[str, float]],
    sequence_number: int,
    target_segment_duration: int,
):
    """Update the master.m3u8 with the given sequence.

    Args:
        sequence: the sequence of segments described by tuples of
            filename (.ts) and duration.
        sequence_number: the position of the first segment with respect
            to the beginning of the recording.
        target_segment_duration: the expected duration of segments.

    """

    with open(os.path.join(MEDIAS_DIR, "0", "master.m3u8"), mode="w") as f:
        f.truncate()
        f.write(
            "#EXTM3U\n"
            f"#EXT-X-TARGETDURATION:{target_segment_duration}\n"
            "#EXT-X-VERSION:4\n"
            f"#EXT-X-MEDIA-SEQUENCE:{sequence_number}\n"
        )
        for filename, duration in sequence:
            f.write(f"#EXTINF:{duration},\n" f"{filename}\n")


def make_stream(chunk_size: int, rate: int, channels: int) -> pyaudio.Stream:
    """Make an audio stream from the default microphone
    """
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=channels,
        rate=rate,
        frames_per_buffer=chunk_size,
        input=True,
    )

    return stream


def make_path_from_media_dir(filename: str) -> str:
    """Make a path to the given filename relative to the media dir.
    """
    return os.path.join(MEDIAS_DIR, "0", filename)


def record(*, target_segment_duration: int = 5, output_queue: multiprocessing.Queue):
    """Record from the default microphone and write segments.

    Write segments as .ts files (MPEG-TS) along with a master.m3u8 playlist.

    """
    rate = 44100
    chunk_size = rate // 10

    stream = make_stream(chunk_size, rate, channels=1)

    while True:
        frames = []
        n_frames = round(target_segment_duration / (chunk_size / rate))
        for _ in range(n_frames):
            data = stream.read(chunk_size, exception_on_overflow=True)
            frames.append(data)

        segment = pydub.AudioSegment(
            data=b"".join(frames), sample_width=2, frame_rate=44100, channels=1
        )

        output_queue.put(segment)


def process_segments(input_queue: multiprocessing.Queue, target_segment_duration):
    sequence_number = 1
    rolling_sequence: List[Tuple[str, float]] = []
    rolling_size = 3
    while True:
        segment = input_queue.get()

        filename = "{}.ts".format(hashlib.sha256(segment.raw_data).hexdigest())
        segment.export(
            make_path_from_media_dir(filename),
            format="mpegts",
            codec="mp2",
            bitrate="64k",
        )

        rolling_sequence.append((filename, len(segment) / 1000))
        if len(rolling_sequence) > rolling_size:
            sequence_number += 1
            os.remove(make_path_from_media_dir(rolling_sequence[0][0]))
            rolling_sequence = rolling_sequence[1:]

        update_playlist(rolling_sequence, sequence_number, target_segment_duration)


q = multiprocessing.Queue()
multiprocessing.Process(
    target=process_segments, args=(q, TARGET_SEGMENT_DURATION)
).start()
record(target_segment_duration=TARGET_SEGMENT_DURATION, output_queue=q)
