import os
import sys

try:
    from tqdm.auto import tqdm
except ImportError:
    print("Trying to Install required module: tqdm\n")
    os.system('pip3 install --user tqdm')
    try:
        from tqdm.auto import tqdm
    except ImportError:
        sys.exit('Please install module tqdm from http://pypi.python.org/pypi/tqdm or run: pip3 install tqdm.')


def question_y(question: str) -> bool:
    """Question prompt default Y."""
    reply = None
    while reply not in ("", "y", "n"):
        reply = input(f"{question} (Y/n): ").lower()
    return reply in ("", "y")


def question_n(question: str) -> bool:
    """Question prompt default N."""
    reply = None
    while reply not in ("", "y", "n"):
        reply = input(f"{question} (y/N): ").lower()
    return reply in ("y", "Y")


def get_download_path(dest_path):
    if dest_path:
        print('Using provided destination: ' + dest_path)
    else:
        """Ask for desired download folder"""
        dest_path = input('Please input destination: ')
        print('Using destination: ' + dest_path)
    return dest_path


def get_progress_bar(total_size_in_bytes):
    return tqdm(total=total_size_in_bytes, unit='iB', unit_scale=True)
