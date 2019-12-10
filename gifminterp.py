import argparse
import tempfile
import subprocess
import shutil
import os
import sys
import glob
from multiprocessing.dummy import Pool as ThreadPool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--loop", type=int, default=50)
    ap.add_argument("--input-fps", type=int, default=24)
    ap.add_argument("--minterpolate-fps", type=int, default=60)
    ap.add_argument("--output-fps", type=int, default=120)
    ap.add_argument("--background", default="white")
    args = ap.parse_args()
    tempdir = tempfile.mkdtemp(prefix="barrot-")
    input_pat = os.path.join(tempdir, "f_%08d.png")
    subprocess.check_call(["magick", "convert", args.input, "-coalesce", input_pat])
    frames = glob.glob(os.path.join(tempdir, "f_*.png"))

    with ThreadPool() as p:
        print(f"flattening {len(frames)} frames using {p._processes} processes...")

        def flatten_frame(frame):
            subprocess.check_call(
                ["magick", "mogrify", "-background", args.background, "-flatten", frame]
            )

        list(p.imap_unordered(flatten_frame, frames))
    print(
        f"running ffmpeg pipeline (it's normal for this to take a while to output anything)..."
    )
    minterp_processor = subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "panic",
            "-stream_loop",
            str(args.loop),
            "-framerate",
            str(args.input_fps),
            "-i",
            input_pat,
            "-vf",
            f"minterpolate=fps={args.minterpolate_fps}",
            "-c:v",
            "png",
            "-f",
            "image2pipe",
            "-",
        ],
        stdout=subprocess.PIPE,
    )
    output_processor = subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-y",
            "-f",
            "image2pipe",
            "-framerate",
            str(args.output_fps),
            "-i",
            "-",
            "-tune",
            "animation",
            "-preset",
            "medium",
            "-crf",
            "24",
            "-pix_fmt",
            "yuv420p",
            args.output,
        ],
        stdin=minterp_processor.stdout,
    )
    minterp_processor.stdout.close()
    output_processor.wait()
    minterp_processor.kill()
    print(f"done! cleaning up {tempdir}")
    shutil.rmtree(tempdir)
    sys.exit(output_processor.returncode)


if __name__ == "__main__":
    main()
