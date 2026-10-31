"""Build the original, texture-free demo GLB using only the standard library.

Run from any directory. No external models or licences required. Keep the
generated asset committed because production has no model generation step.
"""
import json
from pathlib import Path
import struct


def build():
    vertices = (-.5, -.5, -.5, .5, -.5, -.5, .5, .5, -.5, -.5, .5, -.5,
                -.5, -.5, .5, .5, -.5, .5, .5, .5, .5, -.5, .5, .5)
    indices = (0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7, 0, 1, 5, 0, 5, 4,
               3, 7, 6, 3, 6, 2, 0, 4, 7, 0, 7, 3, 1, 2, 6, 1, 6, 5)
    binary = struct.pack('<24f', *vertices) + struct.pack('<36H', *indices)
    parts = [([-0.8, .175, 0], [.55, .35, .55]),
             ([0, .3, 0], [.55, .6, .55]),
             ([.8, .125, 0], [.55, .25, .55])]
    colors = [[.16, .72, .47, 1], [.17, .52, .84, 1], [.85, .59, .24, 1]]
    gltf = {
        'asset': {'version': '2.0', 'generator': 'EcoIQ original demo geometry'},
        'scene': 0, 'scenes': [{'nodes': [0, 1, 2]}],
        'nodes': [{'mesh': i, 'translation': t, 'scale': s}
                  for i, (t, s) in enumerate(parts)],
        'meshes': [{'primitives': [{'attributes': {'POSITION': 0},
                                   'indices': 1, 'material': i}]} for i in range(3)],
        'materials': [{'pbrMetallicRoughness': {'baseColorFactor': c,
                       'metallicFactor': 0, 'roughnessFactor': .8}} for c in colors],
        'buffers': [{'byteLength': len(binary)}],
        'bufferViews': [{'buffer': 0, 'byteOffset': 0, 'byteLength': 96, 'target': 34962},
                        {'buffer': 0, 'byteOffset': 96, 'byteLength': 72, 'target': 34963}],
        'accessors': [{'bufferView': 0, 'componentType': 5126, 'count': 8,
                       'type': 'VEC3', 'min': [-.5, -.5, -.5], 'max': [.5, .5, .5]},
                      {'bufferView': 1, 'componentType': 5123, 'count': 36, 'type': 'SCALAR'}],
    }
    encoded = json.dumps(gltf, separators=(',', ':')).encode()
    encoded += b' ' * (-len(encoded) % 4)
    result = (struct.pack('<III', 0x46546c67, 2, 28 + len(encoded) + len(binary))
              + struct.pack('<II', len(encoded), 0x4e4f534a) + encoded
              + struct.pack('<II', len(binary), 0x004e4942) + binary)
    target = Path(__file__).resolve().parents[1] / 'static/models/stewardship-demo.glb'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result)


if __name__ == '__main__':
    build()
