
DIALOG_NONE = 0
DIALOG_PROGRESS = 1
DIALOG_STATUS = 2
DIALOG_ERROR = 3

LOG_DEBUG = 0
LOG_WARN = 1
LOG_ERROR = 2

ACTION_EXTRACT = 0
ACTION_EXPORT = 1
ACTION_EXTRACT_EXPORT = 2
ACTION_PASS = 3
# ACTION_PERFORM_ON_CHILDREN = 2


# TEX_DIFFUSE = 0x00
# TEX_NORMAL = 0x01
# TEX_AO = 0x02
# TEX_ALPHA = 0x03
# TEX_MASK = 0x04

# DBLD Block tags

TAG_RQRL = 0x4c527152 # RendInst list
TAG_DXP2 = 0x32507844
TAG_TEX = 0x58455400
TAG_TEX_2 = 0x2e584554
TAG_LMAP = 0x70616d6c # Land blend tex
TAG_HM2 = 0x324d4800 # Heightmaps
TAG_LMP2 = 0x32704d4c # Land tex??
TAG_HSPL = 0x6c707368
TAG_SPGZ = 0x7a677073
TAG_STBL = 0x6c627473
TAG_WBBX = 0x58424257
TAG_LNV3 = 0x33766e4c
TAG_CVRS = 0x53525643
TAG_SCN = 0x4e435300 # Scene
TAG_FRT = 0x54524600 # Static collision
TAG_TM24 = 0x34326d74
TAG_RIGZ = 0x7a474952 # RendInstGen
TAG_OBJ = 0x6a624f00
TAG_END = 0x444e4500

SETTINGS_EXPORT_FOLDER = "EXPORT_FOLDER"
SETTINGS_EXPORT_PREVIEW_TEX = "EXPORT_PREVIEW_TEX"
SETTINGS_EXTRACT_FOLDER = "EXTRACT_FOLDER"
SETTINGS_NO_TEX_EXPORT = "NO_TEX_EXPORT"
SETTINGS_OUTPUT_FOLDER = "OUTPUT_FOLDER"
SETTINGS_STUDIOMDL_PATH = "STUDIOMDL_PATH"
SETTINGS_GAMEINFO_PATH = "GAMEINFO_PATH"
SETTINGS_STUDIOMDL_EXPORT_COLLISION = "STUDIOMDL_EXPORT_COLLISION"
SETTINGS_EXPORT_GAMEINFO = "EXPORT_GAMEINFO"
SETTINGS_EXPORT_SMD = "EXPORT_SMD"
SETTINGS_NO_MDL = "NO_MDL"
SETTINGS_DONT_EXPORT_EXISTING_TEXTURES = "DONT_EXPORT_EXISTING_TEXTURES"
SETTINGS_FORCE_DDS_CONVERSION = "FORCE_DDS_CONVERSION"
SETTINGS_EXPAND_ALL = "EXPAND_ALL"

TEXTURE_GENERIC = 0
TEXTURE_NORMAL = 1
TEXTURE_MASKED = 2

MVD_NORMAL = 0
MVD_SKINNED = 1
MVD_SKINNED_FLAG = 2