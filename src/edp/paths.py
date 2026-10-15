"""Utilitarios de caminho compartilhados entre a CLI e a GUI."""

import os


def default_output_path(src: str, suffix: str) -> str:
    """Deriva o caminho de saida padrao a partir do nome da entrada.

    Ex.: ``/jogo/God of War.iso`` + ``"esr"`` -> ``/jogo/God of War_esr.iso``.
    Se a entrada nao tiver extensao, assume ``.iso``.

    Portavel: reconhece tanto ``/`` quanto ``\\`` como separador, de modo que o
    nome e derivado corretamente tambem para caminhos do Windows (``C:\\iso\\jogo.iso``)
    mesmo quando o codigo roda em POSIX. O ``splitext`` e' aplicado apenas ao
    componente final, evitando que um ponto no diretorio (``C:\\my.dir\\jogo``)
    seja confundido com a extensao.
    """
    # Ultimo separador, seja POSIX ('/') ou Windows ('\\').
    sep = max(src.rfind("/"), src.rfind("\\"))
    head, tail = src[:sep + 1], src[sep + 1:]
    root, ext = os.path.splitext(tail)
    return "%s%s_%s%s" % (head, root, suffix, ext or ".iso")
