"""The EROFS superblock, as far as the tests read it: an image's size.

A slot's root partition starts with its EROFS image; the overlay area
fills the rest (test-hygiene D5).
"""

import struct

# struct erofs_super_block, at byte 1024 of the image: its magic, then
# blkszbits at 12 and blocks at 36.
SUPERBLOCK = 1024
FIELDS = struct.Struct("<I8xB23xI")
MAGIC = 0xE0F5E1E2


def size(superblock: bytes) -> int:
    """Return the size of an image, read from its superblock.

    ``superblock`` holds the image's bytes from SUPERBLOCK on, FIELDS'
    size of them at least.
    """
    magic, block_bits, blocks = FIELDS.unpack_from(superblock)
    if magic != MAGIC:
        msg = f"no EROFS superblock (magic {magic:#x})"
        raise ValueError(msg)
    return int(blocks) << int(block_bits)
