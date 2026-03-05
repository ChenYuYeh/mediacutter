# MediaCutter

A Python CLI for cutting/trimming media files with `ffmpeg`.

## Features

- Cut media between start and end timecodes (strict `hh:mm:ss`)
- Batch cut media into fixed-duration sequential clips using `--period` + `--count`
- Optional output filename (default: `<input>_<start>_<end>.<ext>` with `:` replaced by `-`)
- Stream copy mode (`-c copy`) for fast trimming without re-encoding
- Optional `--tv-compatible` mode to transcode to H.264/AAC with TV-friendly MP4 settings
- Progress bar during `--tv-compatible` processing (percent, elapsed, ETA)
- Safety checks:
  - `end` must be greater than `start`
  - output file must be different from input file
  - `--period` and `--count` must be provided together

## Requirements

- Python 3.8+
- Bundled FFmpeg binary at `tools/ffmpeg/ffmpeg.exe`

## FFmpeg Binary

This project vendors FFmpeg at:

```text
tools/ffmpeg/ffmpeg.exe
```

CLI execution prefers this local binary first. You can override it with:

```powershell
$env:MEDIACUTTER_FFMPEG = "C:\path\to\ffmpeg.exe"
```

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .
```

Optional test dependencies:

```bash
pip install -e ".[test]"
```

## Usage

```bash
mediacutter input.mp4 -s 00:01:00 -e 00:02:30
# output: input_00-01-00_00-02-30.mp4

mediacutter input.mkv -s 00:00:10 -e 00:00:20 -o trimmed.mkv

# create 3 clips, each 10 seconds:
# input_01_00-00-00_00-00-10.mp4
# input_02_00-00-10_00-00-20.mp4
# input_03_00-00-20_00-00-30.mp4
mediacutter input.mp4 --period 00:00:10 --count 3

# transcode output for broader smart TV playback compatibility
mediacutter input.mp4 -s 00:01:00 -e 00:02:30 --tv-compatible
```

Notes:
- Time format is strict `hh:mm:ss` (example: `00:01:05`)
- For single-cut mode, `--start` and `--end` must be provided together
- For batch-cut mode, `--period` and `--count` must be provided together
- Do not mix single-cut and batch-cut arguments in one command
- If `-o/--output` is omitted, output is created next to input
- Default mode uses stream copy (`-c copy`); use `--tv-compatible` to transcode (slower, more compatible)

## Development

Run the tests with:

```bash
python -m pytest
```

## Build (Windows)

`build.ps1` creates a standalone executable with PyInstaller and bundles `tools/ffmpeg/ffmpeg.exe`.

```powershell
powershell -ExecutionPolicy Bypass -File .\build.ps1
```

Output:

```text
dist\mediacutter.exe
```

Optional parameters:

```powershell
# custom exe name
powershell -ExecutionPolicy Bypass -File .\build.ps1 -ExeName mediacutter-cli

# custom virtualenv python path
powershell -ExecutionPolicy Bypass -File .\build.ps1 -VenvPython .\.venv\Scripts\python.exe
```

## Contributing

Use feature branches and open pull requests against `main`.

## License

MIT
