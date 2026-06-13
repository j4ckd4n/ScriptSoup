from typing import Optional, Any
import ffmpeg
import argparse

def detect_video_codec(input_path: str) -> str:
    """
    Probes the input file to find the original video codec name.
    """
    try:
        probe = ffmpeg.probe(input_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream and 'codec_name' in video_stream:
            return video_stream['codec_name']
    except Exception as e:
        print(f"Warning: Could not probe file metadata ({e}). Defaulting to h264.")
    
    return 'h264'


def nvec_resize(
    video_stream: Any, 
    audio_stream: Any, 
    output_path: str, 
    scale: str,
    original_codec: str
) -> Any:
    """
    Resizes the video stream and dynamically matches the encoder 
    to the input file's original codec format.
    """
    w, h = scale.split(':')
    
    # Map the original codec to its NVENC equivalent
    if original_codec in ['hevc', 'h265']:
        encoder = 'hevc_nvenc'
    elif original_codec == 'av1':
        encoder = 'av1_nvenc'
    else:
        encoder = 'h264_nvenc'  # Safe fallback for h264 and everything else
        
    print(f"Detected original format: {original_codec.upper()}")
    print(f"Configuring standalone resize ({w}x{h}) using hardware encoder: {encoder}")
    
    resized_video = video_stream.filter('scale', w, h)
    
    return ffmpeg.output(
        resized_video, audio_stream,
        output_path,
        vcodec=encoder,
        hwaccel_output_format='cuda',
        preset='p4',        # Balanced speed/quality preset
        acodec='copy',      # Instant audio transfer without re-encoding
        y=None
    )


def nvec_compress(
    video_stream: Any,
    audio_stream: Any,
    output_path: str,
    codec: str = 'hevc_nvenc',
    preset: str = 'p6',
    rc: str = 'vbr_hq',
    cq: int = 24,
    audio_bitrate: str = '128k',
    maxrate: str = '4M',
    bufsize: str = '8M'
) -> Any:
    """
    Applies custom bitrate and quality compression to the video stream.
    """
    print("Configuring targeted compression profile...")
    return ffmpeg.output(
        video_stream, audio_stream,
        output_path,
        vcodec=codec,
        preset=preset,
        rc=rc,
        cq=str(cq),
        maxrate=maxrate,
        bufsize=bufsize,
        acodec='aac',
        audio_bitrate=audio_bitrate,
        y=None
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Isolate resizing or compressing using NVIDIA NVENC.")
    parser.add_argument("input_path", help="Path to the input video file.")
    parser.add_argument("output_path", help="Path to the output video file.")
    parser.add_argument("--scale", default=None, help="Scale resolution (e.g., '1920:1080').")
    parser.add_argument("--codec", default="hevc_nvenc", help="Video codec to use for compression mode.")
    parser.add_argument("--preset", default="p6", help="Encoding preset.")
    parser.add_argument("--rc", default="vbr_hq", help="Rate control mode.")
    parser.add_argument("--cq", type=int, default=24, help="Constant quantizer value.")
    parser.add_argument("--audio_bitrate", default="128k", help="Audio bitrate.")
    parser.add_argument("--maxrate", default="4M", help="Maximum bitrate.")
    parser.add_argument("--bufsize", default="8M", help="Buffer size.")
    parser.add_argument("--hwaccel", default="cuda", help="Hardware acceleration method.")

    args = parser.parse_args()

    # Initialize input streams
    input_kwargs = {'hwaccel': args.hwaccel} if args.hwaccel else {}
    stream = ffmpeg.input(args.input_path, **input_kwargs)
    video = stream.video
    audio = stream.audio

    # Dynamic Choice Logic
    if args.scale:
        # Detect what the video was using before
        detected_codec = detect_video_codec(args.input_path)
        
        # Scenario A: Just resize, using matching codec family
        output_stream = nvec_resize(
            video_stream=video, 
            audio_stream=audio, 
            output_path=args.output_path, 
            scale=args.scale,
            original_codec=detected_codec
        )
    else:
        # Scenario B: Target compression
        output_stream = nvec_compress(
            video_stream=video,
            audio_stream=audio,
            output_path=args.output_path,
            codec=args.codec,
            preset=args.preset,
            rc=args.rc,
            cq=args.cq,
            audio_bitrate=args.audio_bitrate,
            maxrate=args.maxrate,
            bufsize=args.bufsize
        )

    # Run the selected pipeline
    print("Processing...")
    ffmpeg.run(output_stream)
    print(f"Done: {args.output_path}")