"""Constantes do formato ESR / UDF / ISO9660.

Todos os valores foram levantados das implementacoes de referencia
(esr-disc-patcher, OpenESRDiscPatcher, esrtool). Estao centralizados aqui
para que o formato do patch seja auditavel em um unico lugar.
"""

# --- Geometria de disco (DVD: setor logico de 2048 bytes) ---
SECTOR_SIZE = 2048

# --- Estrutura DVD-Video sintetica embutida no disco ---
DVD_VIDEO_LBA = 128
DVD_VIDEO_SECTORS = 12
DVD_VIDEO_SIZE = DVD_VIDEO_SECTORS * SECTOR_SIZE  # 24576 bytes

# Descritores UDF reescritos pelo patch: (descritor_alvo, LBA_de_backup)
TARGET_DESCRIPTORS = (
    (34, 14),
    (50, 15),
)

# Offset dentro do descritor que guarda a "extent location" (LBA de destino).
EXTENT_LOCATION_OFFSET = 0xBC  # 188

# --- Tag UDF (ECMA-167) ---
TAG_CHECKSUM_OFFSET = 4
TAG_CRC_OFFSET = 8
TAG_CRC_LENGTH_OFFSET = 10
TAG_HEADER_SIZE = 16

# --- Marcador de "ja patchado" (compativel com as ferramentas de referencia) ---
# Apos o patch, o LBA 14 contem a copia do descritor original do LBA 34, que
# contem a string "+NSR" no offset 25.
PATCH_MARKER_LBA = 14
PATCH_MARKER_OFFSET = 25
PATCH_MARKER = b"+NSR"

# --- Volume Recognition Sequence (ECMA-167) ---
VRS_START_SECTOR = 16
VRS_SCAN_SECTORS = 64
VRS_NSR_IDS = (b"NSR02", b"NSR03")

# --- ISO9660 ---
ISO9660_SCAN_SECTORS = 64
ISO9660_MAGIC = b"CD001"
PVD_TYPE = 1
PVD_VOLUME_ID_OFFSET = 40
PVD_VOLUME_ID_LENGTH = 32
PVD_ROOT_RECORD_OFFSET = 156
DIR_RECORD_MIN_LENGTH = 34

# Menor tamanho de imagem que pode conter toda a regiao do patch.
MIN_IMAGE_SIZE = (DVD_VIDEO_LBA + DVD_VIDEO_SECTORS) * SECTOR_SIZE
