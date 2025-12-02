from enum import Enum
import subprocess, shutil
import zipfile
from typing import Callable
from rich.console import Console
from pathlib import Path


class Anchor(Enum):
    BOTTOM = "bottom"
    TOP = "top"
    CENTER = "center"


BG_FILL = "black"
WIDTH, HEIGHT = 800, 1280
INPUT = Path("input.gif")
OUTPUT = Path("bootanimation.zip")
ROOT_PATH = Path("bootanimation")
PART_PATH = ROOT_PATH / "part0"
DESC_FILE = ROOT_PATH / "desc.txt"
ANCHOR: Anchor = Anchor.BOTTOM


def run_command(cmd):
    """Run shell command and return stdout."""
    proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
    return proc.stdout


def convert_gif():
    PART_PATH.mkdir(parents=True, exist_ok=True)

    ffmpeg_cmd = [
        "ffmpeg",
        "-loglevel",
        "quiet",
        "-i",
        str(INPUT.resolve()),
        "-filter_complex",
        "[0:v]split[fg][bg];[bg]format=pix_fmts=rgb24,geq=r='0':g='0':b='0'"
        "[bg_black];[bg_black][fg]overlay=shortest=1[out]",
        "-map",
        "[out]",
        "-q:v",
        "2",
        "-y",
        str(PART_PATH / "out_%03d.jpg"),
    ]
    run_command(ffmpeg_cmd)


def build_pad_y():
    """Return correct Y offset depending on anchor."""
    if ANCHOR == Anchor.TOP:
        return "0"
    elif ANCHOR == Anchor.BOTTOM:
        return "(oh-ih)"
    else:
        return "(oh-ih)/2"


def scale_gif(callback: Callable[[Path], None]):
    """Scale and pad extracted frames."""
    pad_y = build_pad_y()
    files_done = []

    for file in sorted(PART_PATH.glob("out_*.jpg")):
        output = file.with_name(file.name.replace("out_", ""))

        vf = ",".join(
            [
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease",
                f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:{pad_y}:{BG_FILL}",
            ]
        )

        ffmpeg_cmd = [
            "ffmpeg",
            "-loglevel",
            "quiet",
            "-i",
            str(file),
            "-vf",
            vf,
            "-y",
            str(output),
        ]
        run_command(ffmpeg_cmd)

        file.unlink(missing_ok=True)
        callback(output)
        files_done.append(output)

    return files_done


def write_desc():
    """Generate proper desc.txt with automatic framerate."""
    ffprobe_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=r_frame_rate",
        "-of",
        "default=noprint_wrappers=1",
        str(INPUT),
    ]

    out = run_command(ffprobe_cmd).strip()

    try:
        framerate = int(eval(out.split("=")[-1]))
    except:
        framerate = 24  # fallback

    with DESC_FILE.open("w") as f:
        f.write(f"{WIDTH} {HEIGHT} {framerate}\n")
        f.write(f"p 0 0 {PART_PATH.name}\n")


def zip_folder(callback: Callable[[Path], None]):
    files_done = []

    with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_STORED) as zipf:
        # Add desc.txt
        if DESC_FILE.exists():
            zipf.write(DESC_FILE, DESC_FILE.name)
            files_done.append(DESC_FILE)

        # Add frames
        for frame in sorted(PART_PATH.iterdir()):
            # Must include directory inside zip
            zipf.write(frame, f"{PART_PATH.name}/{frame.name}")
            callback(frame)
            files_done.append(frame)

    return files_done


def main():
    console = Console()

    console.print(f"[bold cyan]Converting {INPUT} → {PART_PATH}[/]")
    convert_gif()

    console.print("[bold cyan]Scaling frames...[/]")
    scale_gif(lambda fp: console.print(f"[orange]Scaled:[/] '{fp.name}'"))

    console.print("[bold cyan]Writing desc.txt...[/]")
    write_desc()

    console.print(f"[bold cyan]Creating {OUTPUT}...[/]")
    zip_folder(lambda fp: console.print(f"[orange]Added:[/] '{fp.name}'"))

    console.print("[bold cyan]Deleting temp files...[/]")
    shutil.rmtree(ROOT_PATH)
    console.print(f"[green]Deleted:[/] {ROOT_PATH}/*")

    console.print("[bold green]Done! Bootanimation ready.[/]")

if __name__ == "__main__":
    main()
