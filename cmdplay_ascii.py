import os
import sys
import time
import shutil
from dataclasses import dataclass

import cv2
from PIL import Image
import pygame


# Defaults (can be overridden via CLI)
VIDEO_PATH = "bad_apple.mp4"
AUDIO_PATH = "bad_apple.mp3"

# ASCII aspect ratio compensation: characters are taller than wide
ASCII_HEIGHT_RATIO = 0.45

# Classic light-to-dark ramp (space -> dense)
ASCII_RAMP = " .:-=+*#%@"
# .:!RIHW$@
@dataclass
class RenderConfig:
    target_width: int
    ramp: str = ASCII_RAMP
    height_ratio: float = ASCII_HEIGHT_RATIO


def get_terminal_width(default_width: int = 120) -> int:
    try:
        size = shutil.get_terminal_size(fallback=(default_width, 30))
        # Keep a small margin to avoid wrapping
        return max(20, size.columns - 2)
    except Exception:
        return default_width


def clear_screen():
    # Clear screen and move cursor to home
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()


def enter_alt_screen():
    # Switch to terminal's alternate buffer (reduces flicker)
    sys.stdout.write("\033[?1049h")
    sys.stdout.flush()


def leave_alt_screen():
    # Return to normal buffer
    sys.stdout.write("\033[?1049l")
    sys.stdout.flush()


def hide_cursor():
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


def build_lut(ramp: str) -> list[str]:
    # Deterministic 0..255 -> ramp index mapping (no FP rounding)
    # idx = floor(v * len(ramp) / 256), clamped to len(ramp)-1
    lut: list[str] = []
    n = len(ramp)
    last_idx = n - 1
    for v in range(256):
        idx = (v * n) // 256
        if idx > last_idx:
            idx = last_idx
        lut.append(ramp[idx])
    return lut


def frame_to_ascii(image: Image.Image, ramp: str) -> str:
    # Image is expected to be grayscale
    pixels = image.getdata()
    lut = build_lut(ramp)
    chars = [lut[p] for p in pixels]
    return "".join(chars)


def resize_for_ascii(image: Image.Image, target_width: int, height_ratio: float) -> Image.Image:
    width, height = image.size
    new_height = int((height / width) * target_width * height_ratio)
    if new_height < 1:
        new_height = 1
    # Use NEAREST to avoid interpolation-induced brightness flicker
    return image.resize((target_width, new_height), resample=Image.NEAREST)


def print_ascii_block(ascii_str: str, width: int):
    # Move cursor to home and write the whole frame in one go
    lines = [ascii_str[i:i + width] for i in range(0, len(ascii_str), width)]
    buffer = "\033[H" + "\n".join(lines) + "\n"
    sys.stdout.write(buffer)
    sys.stdout.flush()


def play_ascii_video(video_path: str, audio_path: str, config: RenderConfig) -> None:
    pygame.init()
    pygame.mixer.init()

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    frame_duration = 1.0 / max(1e-6, fps)

    # Optimize terminal output: alternate screen + hide cursor + clear once
    enter_alt_screen()
    hide_cursor()
    clear_screen()

    # Start audio if available
    try:
        if os.path.exists(audio_path):
            pygame.mixer.music.load(audio_path)
            pygame.mixer.music.set_volume(0.25)
            pygame.mixer.music.play()
    except Exception:
        # If audio fails, continue with silent playback
        pass

    start_clock = time.perf_counter()
    frame_index = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Convert to grayscale and denoise slightly to stabilize flat areas
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.medianBlur(gray, 3)
            im = Image.fromarray(gray)
            im = resize_for_ascii(im, config.target_width, config.height_ratio)
            ascii_str = frame_to_ascii(im, config.ramp)

            print_ascii_block(ascii_str, im.width)

            # Sync to FPS using wall clock
            frame_index += 1
            target_time = start_clock + frame_index * frame_duration
            now = time.perf_counter()
            if target_time > now:
                time.sleep(target_time - now)

            # Early exit if audio finished and we've printed some frames
            if frame_index > 10 and not pygame.mixer.music.get_busy():
                break
    finally:
        cap.release()
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
        pygame.quit()
        # Restore terminal state
        show_cursor()
        leave_alt_screen()


def main(argv: list[str]) -> None:
    # CLI: python cmdplay_ascii.py [video_path] [audio_path] [width]
    video_path = argv[1] if len(argv) > 1 else VIDEO_PATH
    audio_path = argv[2] if len(argv) > 2 else AUDIO_PATH

    if len(argv) > 3:
        try:
            width = int(argv[3])
        except ValueError:
            width = get_terminal_width()
    else:
        width = get_terminal_width()

    config = RenderConfig(target_width=width)
    play_ascii_video(video_path, audio_path, config)


if __name__ == "__main__":
    main(sys.argv)


