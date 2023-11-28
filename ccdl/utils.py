import zipfile


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


def get_download_path(path):
    if path:
        if path.lower() == 'ask':
            """Ask for desired download folder"""
            path = input('Please input destination: ')
            print('Using destination: ' + path)
        else:
            print('Using provided destination: ' + path)
    return path


def check_archive(path):
    ok = None

    if path[-4:] == '.zip':
        print('checking zip archive ... ', end='', flush=True)
        if zipfile.is_zipfile(path):
            ok = zipfile.ZipFile(path).testzip() is None
        else:
            ok = False

    if ok is True:
        print('OK')
    elif ok is False:
        print('Error')
    return ok
