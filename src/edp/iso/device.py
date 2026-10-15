"""Abstracao de acesso aleatorio a uma imagem (arquivo ou memoria).

A engine de patch depende apenas do contrato ``RandomAccessDevice`` (DIP),
de modo que o mesmo codigo serve para arquivo real e para testes em memoria.
"""

import os
from typing import Protocol, runtime_checkable

from ..domain.errors import DeviceError


@runtime_checkable
class RandomAccessDevice(Protocol):
    """Contrato minimo para leitura/escrita posicional."""

    def size(self) -> int:
        ...

    def read_at(self, offset: int, length: int) -> bytes:
        ...

    def write_at(self, offset: int, data) -> None:
        ...

    def flush(self) -> None:
        ...


class FileDevice:
    """Implementa ``RandomAccessDevice`` sobre um arquivo real."""

    def __init__(self, path: str, mode: str = "rb"):
        if mode not in ("rb", "r+b", "rb+", "wb+", "w+b"):
            raise DeviceError("modo de arquivo nao suportado: %s" % mode)
        self.path = path
        self.mode = mode
        self._fh = open(path, mode)

    def size(self) -> int:
        return os.fstat(self._fh.fileno()).st_size

    def read_at(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0:
            raise DeviceError("offset/length negativo")
        self._fh.seek(offset)
        data = self._fh.read(length)
        if len(data) != length:
            raise DeviceError(
                "leitura curta em %d (pedido %d, obtido %d)" % (offset, length, len(data))
            )
        return data

    def write_at(self, offset: int, data) -> None:
        if offset < 0:
            raise DeviceError("offset negativo")
        self._fh.seek(offset)
        written = self._fh.write(bytes(data))
        if written != len(data):
            raise DeviceError(
                "escrita curta em %d (pedido %d, gravado %d)" % (offset, len(data), written)
            )

    def flush(self) -> None:
        self._fh.flush()

    def close(self) -> None:
        if not self._fh.closed:
            self._fh.close()

    def __enter__(self) -> "FileDevice":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


class MemoryDevice:
    """Implementa ``RandomAccessDevice`` sobre um buffer em memoria."""

    def __init__(self, initial: bytes = b""):
        self._buf = bytearray(initial)

    def size(self) -> int:
        return len(self._buf)

    def read_at(self, offset: int, length: int) -> bytes:
        if offset < 0 or length < 0:
            raise DeviceError("offset/length negativo")
        end = offset + length
        if end > len(self._buf):
            raise DeviceError("leitura alem do fim do buffer")
        return bytes(self._buf[offset:end])

    def write_at(self, offset: int, data) -> None:
        if offset < 0:
            raise DeviceError("offset negativo")
        end = offset + len(data)
        if end > len(self._buf):
            raise DeviceError("escrita alem do fim do buffer")
        self._buf[offset:end] = data

    def flush(self) -> None:
        pass

    def to_bytes(self) -> bytes:
        return bytes(self._buf)
