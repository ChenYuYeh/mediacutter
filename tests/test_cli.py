import pytest
from pathlib import Path

from mediacutter import cli


def test_parse_timecode_valid():
    assert cli.parse_timecode("00:01:05") == "00:01:05"
    assert cli.parse_timecode("12:34:56") == "12:34:56"


def test_parse_timecode_invalid_format():
    with pytest.raises(ValueError):
        cli.parse_timecode("1:2")

    with pytest.raises(ValueError):
        cli.parse_timecode("abc")
    with pytest.raises(ValueError):
        cli.parse_timecode("0:1:5")


def test_build_output_name(tmp_path):
    inp = tmp_path / "video.mp4"
    out = cli.build_output_name(inp, "00:00:10", "00:00:20")
    assert out.name == "video_00-00-10_00-00-20.mp4"


def test_timecode_to_seconds():
    assert cli.timecode_to_seconds("00:00:00") == 0
    assert cli.timecode_to_seconds("01:02:03") == 3723


def test_seconds_to_timecode():
    assert cli.seconds_to_timecode(0) == "00:00:00"
    assert cli.seconds_to_timecode(3723) == "01:02:03"


def test_build_output_kwargs_default_mode():
    assert cli.build_output_kwargs(False) == {"c": "copy"}


def test_build_output_kwargs_tv_compatible_mode():
    assert cli.build_output_kwargs(True) == {
        "vcodec": "libx264",
        "acodec": "aac",
        "pix_fmt": "yuv420p",
        "movflags": "+faststart",
    }


def test_run_ffmpeg_cut(tmp_path):
    # ensure the ffmpeg-python wrapper is available
    pytest.importorskip("ffmpeg")

    inp = tmp_path / "dummy.mp4"
    # create an empty file just for path validity
    inp.write_text("")
    out = tmp_path / "out.mp4"
    with pytest.raises(RuntimeError):
        cli.run_ffmpeg_cut(inp, "00:00:00", "00:00:01", out)


def test_main_rejects_end_not_after_start(tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-s", "00:00:10", "-e", "00:00:10"])
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-s", "00:00:10", "-e", "00:00:09"])


def test_main_rejects_output_same_as_input(tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-s", "00:00:00", "-e", "00:00:01", "-o", str(inp)])


def test_main_calls_run_ffmpeg_cut(monkeypatch, tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    calls = []

    def fake_run(input_file, start, end, output_file, tv_compatible=False):
        calls.append((input_file, start, end, output_file, tv_compatible))

    monkeypatch.setattr(cli, "run_ffmpeg_cut", fake_run)
    cli.main([str(inp), "-s", "00:00:00", "-e", "00:00:01"])
    assert len(calls) == 1
    assert calls[0][4] is False


def test_main_rejects_start_without_end(tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-s", "00:00:00"])


def test_main_rejects_end_without_start(tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-e", "00:00:01"])


def test_main_rejects_period_without_count(tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-p", "00:00:05"])


def test_main_rejects_count_without_period(tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-c", "3"])


def test_main_rejects_mixed_modes(tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-s", "00:00:00", "-e", "00:00:05", "-p", "00:00:05", "-c", "2"])


def test_main_rejects_non_positive_count(tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-p", "00:00:05", "-c", "0"])


def test_main_rejects_zero_period(tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    with pytest.raises(SystemExit):
        cli.main([str(inp), "-p", "00:00:00", "-c", "2"])


def test_main_calls_run_ffmpeg_cut_batch_mode(monkeypatch, tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    calls = []

    def fake_run(input_file, start, end, output_file, tv_compatible=False):
        calls.append((input_file, start, end, output_file, tv_compatible))

    monkeypatch.setattr(cli, "run_ffmpeg_cut", fake_run)
    cli.main([str(inp), "-p", "00:00:05", "-c", "3"])

    assert len(calls) == 3
    assert calls[0][1] == "00:00:00"
    assert calls[0][2] == "00:00:05"
    assert calls[1][1] == "00:00:05"
    assert calls[1][2] == "00:00:10"
    assert calls[2][1] == "00:00:10"
    assert calls[2][2] == "00:00:15"
    assert calls[0][4] is False


def test_main_calls_run_ffmpeg_cut_tv_compatible(monkeypatch, tmp_path):
    inp = tmp_path / "video.mp4"
    inp.write_text("")
    calls = []

    def fake_run(input_file, start, end, output_file, tv_compatible=False):
        calls.append((input_file, start, end, output_file, tv_compatible))

    monkeypatch.setattr(cli, "run_ffmpeg_cut", fake_run)
    cli.main([str(inp), "-s", "00:00:00", "-e", "00:00:01", "--tv-compatible"])

    assert len(calls) == 1
    assert calls[0][4] is True
