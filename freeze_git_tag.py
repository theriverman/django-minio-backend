import re
import sys
import signal
import subprocess


def signal_handler(_, __):
    print('\n----------------------------------------------')
    print('Exiting. No tag will be written to setup.py')
    sys.exit(0)


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal_handler)

    git_tag = subprocess.check_output(['git', 'describe', '--tags']).strip().decode('utf-8')
    pattern = re.compile(r"CURRENT_GIT_TAG = '(v[1-9.]+)'")

    if '--silent' not in sys.argv:
        print('----------------------------------------------')
        print(f'Tag {git_tag} will be written to setup.py')
        input('Press ENTER to continue or Ctrl+C to stop...')
        print('----------------------------------------------')

    with open('setup.py', 'r+') as f:
        old_contents = f.read()
        try:
            f.seek(0)
            new_contents = re.sub(pattern, f"CURRENT_GIT_TAG = '{git_tag}'", old_contents)
            f.write(new_contents)
            f.truncate()
        except (OSError, ValueError):
            f.write(old_contents)
