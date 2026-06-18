"""历史查看器：prompt_toolkit radiolist_dialog 实现"""

from pathlib import Path

from prompt_toolkit.shortcuts import radiolist_dialog

from .config import get_history_dir, I18n

def show_history(target_lang: str = "Chinese"):
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

	try:
		result = radiolist_dialog(
			title=I18n(target_lang)(1),
			text=I18n(target_lang)(1),
			values=entries,
		).run()
	except KeyboardInterrupt:
		return

	if result is None:
		return

	_view_full_result(Path(result), target_lang)

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

def _view_full_result(filepath, target_lang):
	try:
		content = filepath.read_text(encoding="utf-8")
	except Exception:
		print(I18n(target_lang)(1))
		return

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
