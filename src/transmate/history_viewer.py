"""历史查看器：prompt_toolkit radiolist_dialog 实现"""

from pathlib import Path

from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.styles import Style

from .config import get_history_dir


def show_history():
    history_dir = get_history_dir()
    if not history_dir.exists():
        return

    output_files = sorted(
        history_dir.glob("*_output.md"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    if not output_files:
        return

    entries = []
    for f in output_files:
        sid = f.stem.replace("_output", "")
        timestamp = sid[:12]
        summary = _extract_summary(f)
        display = f"{_fmt_time(timestamp)}  {summary[:72]}"
        entries.append((str(f), display))

    dialog_style = Style.from_dict({
        "dialog": "bg:#1a1a2e",
        "dialog.body": "bg:#16213e",
        "dialog.shadow": "bg:#0f0f23",
        "radiolist": "bg:#16213e",
        "button.focused": "bg:#e94560",
    })

    result = radiolist_dialog(
        title="Translation History",
        text="j/k navigate  Enter view  q quit",
        values=entries,
        style=dialog_style,
    ).run()

    if result is None:
        return

    _view_full_result(Path(result))


def _extract_summary(filepath):
    try:
        content = filepath.read_text(encoding="utf-8")
        for line in content.split("\n"):
            if line.startswith("> Input:") or line.startswith("> Input"):
                continue
            stripped = line.strip()
            if stripped and not stripped.startswith("`") and not stripped.startswith("---"):
                return stripped[:100]
    except Exception:
        pass
    return "(empty)"


def _fmt_time(raw):
    try:
        y = "20" + raw[0:2]
        m = raw[2:4]
        d = raw[4:6]
        h = raw[6:8]
        mi = raw[8:10]
        return f"{y}-{m}-{d} {h}:{mi}"
    except Exception:
        return raw


def _view_full_result(filepath):
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception:
        print("Failed to read history file.")
        return

    # 显示最近的翻译记录
    import subprocess
    import tempfile

    tmp = Path(tempfile.gettempdir()) / f"transmate_view_{filepath.stem}.md"
    tmp.write_text(content, encoding="utf-8")

    pager = "less"
    try:
        subprocess.call([pager, "-R", str(tmp)])
    except FileNotFoundError:
        print(content[-2000:])

    tmp.unlink(missing_ok=True)
