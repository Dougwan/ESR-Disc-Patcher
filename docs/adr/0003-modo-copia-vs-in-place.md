# ADR-0003 — Patch por cópia (não destrutivo) como padrão; in-place opcional

- **Status:** Aceito
- **Data:** 2026-10-14

## Contexto

Ferramentas como `esrtool` fazem patch **in-place**, o que é lossy e destrói a
imagem original (o próprio README do esrtool alerta para isso). Já o
`OpenESRDiscPatcher` copia e depois aplica.

## Decisão

- **Padrão:** `patch_to_new_file(origem, destino)` — copia a origem para o
  destino em streaming e aplica o patch no destino. A origem nunca é tocada.
- **Opcional:** `patch_in_place(path)` para quem sabe o que faz.
- O núcleo (`engine`) trabalha sobre `RandomAccessDevice`, então os dois modos
  reutilizam exatamente a mesma lógica.

## Justificativa

- Preserva o arquivo original (segurança/arquivamento).
- O patch toca só os primeiros ~288 KB; a cópia é o único O(tamanho) e é
  limitada pelo disco, não pela linguagem.

## Consequências

- Modo cópia requer espaço livre em disco equivalente ao da ISO.
- A engine é agnóstica de modo (DIP): não muda entre cópia e in-place.
