"""Explicit download of the pinned official benchmark model (no source code)."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

MODEL_ID = 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
REVISION = 'e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
FILES = {'model.onnx': 'onnx/model_quint8_avx2.onnx', 'tokenizer.json': 'tokenizer.json'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name, remote in FILES.items():
        target = args.destination / name
        temporary = target.with_suffix(target.suffix + '.partial')
        with urlopen(f'https://huggingface.co/{MODEL_ID}/resolve/{REVISION}/{remote}', timeout=60) as response, temporary.open('wb') as output:
            while block := response.read(1024 * 1024):
                output.write(block)
        temporary.replace(target)
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
        print(f'Downloaded {name}', flush=True)
    (args.destination / 'manifest.json').write_text(json.dumps({
        'model_id': MODEL_ID, 'revision': REVISION, 'artifact': FILES['model.onnx'], 'sha256': hashes,
    }, indent=2) + '\n')


if __name__ == '__main__':
    main()
