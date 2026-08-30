from pathlib import Path
import sys


def transform(src: Path, dst: Path) -> None:
    s = src.read_text(encoding='utf-8')
    s = s.replace('R10.2', 'R10.3').replace('R10_2', 'R10_3')

    marker = 'Type: files; Name: "{app}\\AUTOLEDGER '
    lines = s.splitlines()
    out = []
    inserted_delete = False
    for line in lines:
        out.append(line)
        if (not inserted_delete and line.startswith(marker) and 'R10.1 TEST.exe' in line):
            out.append(line.replace('R10.1 TEST.exe', 'R10.2 TEST.exe'))
            inserted_delete = True
    s = '\n'.join(out) + ('\n' if s.endswith('\n') else '')

    lines = s.splitlines()
    out = []
    inserted_detection = False
    for line in lines:
        if (not inserted_detection and 'FileExists(' in line and 'R10.3 TEST.exe' in line):
            out.append(line.replace('R10.3 TEST.exe', 'R10.2 TEST.exe'))
            inserted_detection = True
        out.append(line)
    s = '\n'.join(out) + ('\n' if s.endswith('\n') else '')

    if 'R10.2 TEST.exe' not in s:
        raise RuntimeError(f'{src}: R10.2 compatibility was not inserted')
    if 'R10.3 TEST.exe' not in s:
        raise RuntimeError(f'{src}: R10.3 current executable missing')
    dst.write_text(s, encoding='utf-8')
    print(f'{src} -> {dst}')


def main(argv):
    if len(argv) != 3:
        raise SystemExit('usage: installer_transform_r103.py SOURCE_R10_2.iss DEST_R10_3.iss')
    transform(Path(argv[1]), Path(argv[2]))


if __name__ == '__main__':
    main(sys.argv)
