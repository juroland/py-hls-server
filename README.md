# HTTP Live Streaming : trivial server test

## Generate audio segments

Generate 10 seconds segments :

```BASH
ffmpeg -i input.mp3 -start_number 0 -hls_time 10 -hls_list_size 0 -hls_segment_filename "%d.ts" -f hls master.m3u8
```

## Run the live server

```BASH
uvicorn main:app --reload
```

## Access the live stream

For example, we can use `parole` :

```BASH
parole http://127.0.0.1:8000/medias/1/stream/
```
