"""Transformacao pura de um descritor UDF de 2048 bytes.

Toda a aritmetica binaria do patch vive aqui, sem I/O, o que torna a parte
mais delicada 100% testavel de forma isolada.
"""

from ..domain import constants as C
from ..domain.crc import crc16_xmodem
from ..domain.errors import IsoStructureError


def recompute_tag_checksums(block: bytearray) -> None:
    """Recalcula DescriptorCRC (bytes 8-9) e TagChecksum (byte 4) in-place.

    Segue a definicao do tag ECMA-167 usado pela UDF.
    """
    if len(block) != C.SECTOR_SIZE:
        raise IsoStructureError("descritor deve ter %d bytes" % C.SECTOR_SIZE)

    crc_length = int.from_bytes(
        block[C.TAG_CRC_LENGTH_OFFSET:C.TAG_CRC_LENGTH_OFFSET + 2], "little"
    )
    crc = crc16_xmodem(block[C.TAG_HEADER_SIZE:C.TAG_HEADER_SIZE + crc_length])
    block[C.TAG_CRC_OFFSET:C.TAG_CRC_OFFSET + 2] = crc.to_bytes(2, "little")

    checksum = (sum(block[0:C.TAG_HEADER_SIZE]) - block[C.TAG_CHECKSUM_OFFSET]) & 0xFF
    block[C.TAG_CHECKSUM_OFFSET] = checksum


def patch_directory_descriptor(block: bytes, target_lba: int) -> bytes:
    """Reescreve o descritor de diretorio para apontar para ``target_lba``.

    Escreve a "extent location" (bytes 188-189) e atualiza o tag.
    Idempotente: aplicar duas vezes produz o mesmo resultado.
    """
    if len(block) != C.SECTOR_SIZE:
        raise IsoStructureError("descritor deve ter %d bytes" % C.SECTOR_SIZE)
    if not 0 <= target_lba <= 0xFFFF:
        raise IsoStructureError("target_lba fora do intervalo suportado")

    patched = bytearray(block)
    patched[C.EXTENT_LOCATION_OFFSET] = target_lba & 0xFF
    patched[C.EXTENT_LOCATION_OFFSET + 1] = (target_lba >> 8) & 0xFF
    recompute_tag_checksums(patched)
    return bytes(patched)
