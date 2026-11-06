"""Stage the immutable crates.io release; deploy.py owns binary backup/restore."""
import argparse
import hashlib
import io
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

VERSION = '3.5.1'
SHA256 = '45afe16bc8c14dab61ff2acf885034664a6b917ca2ea874ff24eb5107d311ecc'
URL = f'https://static.crates.io/crates/wallust/wallust-{VERSION}.crate'


def compatible():
    if not shutil.which('wallust'):
        return False
    result = subprocess.run(['wallust', '--version'], text=True, capture_output=True, timeout=15)
    return result.returncode == 0 and re.match(r'wallust 3\.5\.1(?:\s|$)', result.stdout) is not None


def stage(output):
    output = Path(output).resolve(strict=True)
    if not output.is_dir():
        raise ValueError('Staging directory required')
    if compatible():
        return
    with tempfile.TemporaryDirectory(prefix='hyprixe-wallust-') as directory:
        build = Path(directory)
        with urllib.request.urlopen(URL, timeout=60) as response:
            archive = response.read()
        if hashlib.sha256(archive).hexdigest() != SHA256:
            raise ValueError('Wallust release SHA-256 mismatch')
        with tarfile.open(fileobj=io.BytesIO(archive)) as source:
            source.extractall(build, filter='data')
        release = build / f'wallust-{VERSION}'
        subprocess.run(['cargo', 'build', '--release', '--locked'], cwd=release, check=True)
        binary = release / 'target/release/wallust'
        check = subprocess.run([str(binary), '--version'], check=True, text=True, capture_output=True)
        if not re.match(r'wallust 3\.5\.1(?:\s|$)', check.stdout):
            raise ValueError('Unexpected built Wallust version')
        shutil.copyfile(binary, output / 'wallust')
        (output / 'wallust').chmod(0o755)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--staging', type=Path)
    args = parser.parse_args()
    if args.check:
        if not compatible():
            parser.exit(1, f'ERROR: Wallust {VERSION} required; run ./install.sh native without --no-packages.\n')
    elif args.staging:
        stage(args.staging)
    else:
        parser.error('--check or --staging required')
