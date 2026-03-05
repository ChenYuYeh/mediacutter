import argparse
import re
import shutil
import threading
import time
import sys
from pathlib import Path

# use the ffmpeg-python wrapper to invoke ffmpeg more reliably
import ffmpeg


def format_seconds(seconds: float) -> str:
    """Format seconds as hh:mm:ss."""
    total = max(0, int(seconds))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def parse_ffmpeg_out_time(out_time: str) -> float:
    """Parse ffmpeg out_time (hh:mm:ss.microseconds) into seconds."""
    match = re.fullmatch(r"(\d+):(\d{2}):(\d{2})(?:\.(\d+))?", out_time)
    if not match:
        return 0.0
    h = int(match.group(1))
    m = int(match.group(2))
    s = int(match.group(3))
    frac = match.group(4) or "0"
    fraction = float(f"0.{frac}")
    return h * 3600 + m * 60 + s + fraction


def print_progress(processed: float, total: float, started_at: float) -> None:
    """Render a single-line terminal progress bar."""
    if total <= 0:
        return
    ratio = min(max(processed / total, 0.0), 1.0)
    width = 28
    filled = int(width * ratio)
    bar = "=" * filled + "-" * (width - filled)
    elapsed = time.time() - started_at
    eta = 0.0
    if processed > 0:
        eta = (elapsed / processed) * max(0.0, total - processed)
    message = (
        f"\r[{bar}] {ratio * 100:5.1f}% "
        f"elapsed {format_seconds(elapsed)} eta {format_seconds(eta)}"
    )
    print(message, end="", flush=True)


def parse_timecode(tc: str) -> str:
    """Validate and return a strict timecode in hh:mm:ss format."""
    if not re.fullmatch(r"\d{2}:\d{2}:\d{2}", tc):
        raise ValueError(f"Timecode must be in hh:mm:ss format: '{tc}'")
    parts = tc.split(":")
    try:
        h, m, s = (int(p) for p in parts)
    except ValueError:
        raise ValueError(f"Timecode contains non-integer values: '{tc}'")
    if m < 0 or m >= 60 or s < 0 or s >= 60 or h < 0:
        raise ValueError(f"Timecode components out of range: '{tc}'")
    return f"{h:02d}:{m:02d}:{s:02d}"


def timecode_to_seconds(tc: str) -> int:
    """Convert a validated hh:mm:ss timecode to total seconds."""
    h, m, s = (int(p) for p in tc.split(":"))
    return h * 3600 + m * 60 + s


def build_output_name(input_path: Path, start: str, end: str) -> Path:
    stem = input_path.stem
    suffix = input_path.suffix
    return input_path.with_name(f"{stem}_{start.replace(':', '-')}_{end.replace(':', '-')}{suffix}")


def seconds_to_timecode(seconds: int) -> str:
    """Convert total seconds to hh:mm:ss timecode."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def build_output_name_with_index(input_path: Path, start: str, end: str, index: int) -> Path:
    stem = input_path.stem
    suffix = input_path.suffix
    return input_path.with_name(
        f"{stem}_{index:02d}_{start.replace(':', '-')}_{end.replace(':', '-')}{suffix}"
    )


def resolve_ffmpeg_binary() -> str:
    """Resolve ffmpeg path, preferring bundled binary in frozen builds."""
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            bundled = Path(meipass) / "ffmpeg.exe"
            if bundled.exists():
                return str(bundled)
        adjacent = Path(sys.executable).with_name("ffmpeg.exe")
        if adjacent.exists():
            return str(adjacent)
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return ffmpeg_path
    raise RuntimeError("ffmpeg binary was not found on PATH")


def run_ffmpeg_cut(
    input_file: Path, start: str, end: str, output_file: Path, tv_compatible: bool = False
) -> None:
    """Trim the media file using ffmpeg-python.

    This will still call the external ``ffmpeg`` binary under the hood, but
    provides a nicer Python interface and automatically builds the command
    line.  Outputs are overwritten if they already exist.
    """
    ffmpeg_cmd = resolve_ffmpeg_binary()
    output_kwargs = {"c": "copy"}
    if tv_compatible:
        output_kwargs = {
            "c": "copy",
            "movflags": "+faststart",
        }
    try:
        duration_seconds = float(timecode_to_seconds(end) - timecode_to_seconds(start))
        process = (
            ffmpeg
            .input(str(input_file), ss=start, to=end)
            .output(str(output_file), **output_kwargs)
            .global_args("-progress", "pipe:1", "-nostats", "-loglevel", "error")
            .overwrite_output()
            .run_async(cmd=ffmpeg_cmd, pipe_stdout=True, pipe_stderr=True)
        )
        stderr_chunks = []

        def collect_stderr() -> None:
            if process.stderr is None:
                return
            while True:
                chunk = process.stderr.read(1024)
                if not chunk:
                    break
                stderr_chunks.append(chunk)

        stderr_thread = threading.Thread(target=collect_stderr, daemon=True)
        stderr_thread.start()

        show_progress = sys.stdout.isatty() and tv_compatible
        started_at = time.time()
        if process.stdout is not None:
            while True:
                raw = process.stdout.readline()
                if not raw:
                    break
                line = raw.decode(errors="ignore").strip()
                if not line or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if show_progress and key == "out_time_ms":
                    processed = max(0.0, int(value) / 1_000_000.0)
                    print_progress(processed, duration_seconds, started_at)
                elif show_progress and key == "out_time":
                    processed = parse_ffmpeg_out_time(value)
                    print_progress(processed, duration_seconds, started_at)
                elif show_progress and key == "progress" and value == "end":
                    print_progress(duration_seconds, duration_seconds, started_at)

        return_code = process.wait()
        stderr_thread.join(timeout=1.0)
        if show_progress:
            print()
        if return_code != 0:
            stderr = b"".join(stderr_chunks).decode(errors="ignore")
            raise RuntimeError(f"ffmpeg failed: {stderr or 'unknown ffmpeg error'}")
    except ffmpeg.Error as e:
        # ffmpeg-python raises its own Error when the process exits non-zero
        stderr = ""
        if getattr(e, "stderr", None):
            stderr = e.stderr.decode(errors="ignore")
        raise RuntimeError(f"ffmpeg failed: {stderr or e}")


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Cut or trim a media file between two timecodes."
    )
    parser.add_argument("input", help="Path to input video (mp4/mkv) file")
    parser.add_argument(
        "-s",
        "--start",
        help="Start time in hh:mm:ss",
    )
    parser.add_argument(
        "-e",
        "--end",
        help="End time in hh:mm:ss",
    )
    parser.add_argument(
        "-p",
        "--period",
        help="Fixed clip duration in hh:mm:ss for batch cutting mode",
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        help="Number of clips to generate in batch cutting mode",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output file path. Defaults to input_start-end.ext",
    )
    parser.add_argument(
        "--tv-compatible",
        action="store_true",
        help="Transcode to H.264/AAC with TV-friendly MP4 settings",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    if not input_path.exists():
        parser.error(f"Input file does not exist: {input_path}")

    single_mode = args.start is not None or args.end is not None
    batch_mode = args.period is not None or args.count is not None

    if single_mode and batch_mode:
        parser.error("Use either --start/--end or --period/--count, not both")

    if not single_mode and not batch_mode:
        parser.error("Provide either --start/--end or --period/--count")

    if single_mode:
        if args.start is None or args.end is None:
            parser.error("--start and --end must be provided together")

        try:
            start_tc = parse_timecode(args.start)
            end_tc = parse_timecode(args.end)
        except ValueError as err:
            parser.error(str(err))

        if timecode_to_seconds(end_tc) <= timecode_to_seconds(start_tc):
            parser.error("End time must be greater than start time")

        if args.output:
            output_path = Path(args.output)
        else:
            output_path = build_output_name(input_path, start_tc, end_tc)

        if output_path.resolve() == input_path.resolve():
            parser.error("Output file must be different from input file")

        run_ffmpeg_cut(
            input_path, start_tc, end_tc, output_path, tv_compatible=args.tv_compatible
        )
        print(f"Created {output_path}")
        return

    if args.period is None or args.count is None:
        parser.error("--period and --count must be provided together")

    if args.count <= 0:
        parser.error("--count must be greater than 0")

    if args.output:
        parser.error("--output is not supported with --period/--count mode")

    try:
        period_tc = parse_timecode(args.period)
    except ValueError as err:
        parser.error(str(err))

    period_seconds = timecode_to_seconds(period_tc)
    if period_seconds <= 0:
        parser.error("--period must be greater than 00:00:00")

    current_start = 0
    for i in range(args.count):
        start_tc = seconds_to_timecode(current_start)
        end_tc = seconds_to_timecode(current_start + period_seconds)
        output_path = build_output_name_with_index(input_path, start_tc, end_tc, i + 1)

        if output_path.resolve() == input_path.resolve():
            parser.error("Output file must be different from input file")

        run_ffmpeg_cut(
            input_path, start_tc, end_tc, output_path, tv_compatible=args.tv_compatible
        )
        print(f"Created {output_path}")
        current_start += period_seconds


if __name__ == "__main__":
    main()
