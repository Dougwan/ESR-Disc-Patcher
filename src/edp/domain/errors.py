"""Hierarquia de erros tipados do edp."""


class EsrError(Exception):
    """Erro base do dominio edp."""


class DeviceError(EsrError):
    """Falha de leitura/escrita no dispositivo de blocos."""


class PathError(EsrError):
    """Caminho de arquivo invalido/inexistente ou saida insegura."""


class IsoStructureError(EsrError):
    """A imagem nao possui a estrutura minima esperada (tamanho/leiaute)."""


class NotUdfError(EsrError):
    """A imagem nao contem a Volume Recognition Sequence UDF."""


class AlreadyPatchedError(EsrError):
    """A imagem ja possui o patch ESR aplicado."""


class NotPatchedError(EsrError):
    """A imagem nao possui o patch ESR aplicado."""


class ElfFormatError(EsrError):
    """O arquivo nao e um ELF valido / esta truncado."""


class DvdDataError(EsrError):
    """O blob DVD-Video embutido esta ausente ou corrompido."""


class FdvdbError(EsrError):
    """Falha ao aplicar o overlay FreeDVDBoot (payload/estrutura)."""
