import datetime
import subprocess


if __name__ == '__main__':
    with open('setup.py', 'r', encoding='utf-8') as f:
        git_tag = subprocess.check_output(['git', 'describe', '--tags']).strip().decode('utf-8')
        year = datetime.datetime.now().year

        contents = f.read()
        contents = contents.replace('{{ VERSION_FROM_GIT_TAG }}', git_tag)
        contents = contents.replace('{{ CURRENT_DATE_YEAR }}', str(year))

    with open('setup.py', 'w', encoding='utf-8') as f:
        f.write(contents)
