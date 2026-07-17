"""
Convert _dps.sav from old format (v0.6/v0.7) to v1.0 format.
Adds missing fields that v1.0 servers require.

Use this if you can't load the co-op save locally to convert it.

Usage:
    python convert_dps_to_v1.py <path_to_dps.sav>

Example:
    python convert_dps_to_v1.py ./Players/A85952B8000000000000000000000000_dps.sav
"""

import os
import sys
import struct
import argparse

PST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PalworldSaveTools", "src")
if os.path.exists(PST_PATH):
    sys.path.insert(0, PST_PATH)
else:
    print("ERROR: PalworldSaveTools folder not found!")
    print("Clone it: git clone https://github.com/deafdudecomputers/PalworldSaveTools.git")
    sys.exit(1)

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS, PALWORLD_CUSTOM_PROPERTIES
try:
    from palworld_save_tools.paltypes import SKP_PALWORLD_CUSTOM_PROPERTIES
    CUSTOM_PROPS = SKP_PALWORLD_CUSTOM_PROPERTIES
except ImportError:
    CUSTOM_PROPS = PALWORLD_CUSTOM_PROPERTIES


def decompress(data):
    ul = int.from_bytes(data[0:4], byteorder="little")
    cl = int.from_bytes(data[4:8], byteorder="little")
    magic = data[8:11]
    save_type = data[11]

    if magic == b"PlM":
        import ooz
        raw = ooz.decompress(data[12:12 + cl], ul)
    elif magic == b"PlZ":
        import zlib
        raw = zlib.decompress(data[12:])
    else:
        raise Exception(f"Unknown format: {magic}")

    return raw, save_type, magic


def compress(raw, save_type, magic):
    if magic == b"PlM":
        import ooz
        compressed = ooz.compress(9, 4, raw, len(raw))
    elif magic == b"PlZ":
        import zlib
        compressed = zlib.compress(raw)
    else:
        raise Exception(f"Unknown format: {magic}")

    header = struct.pack("<II", len(raw), len(compressed))
    header += magic
    header += bytes([save_type])
    return header + compressed


def add_v1_fields(entry):
    """Add missing v1.0 fields to a Pal entry."""
    sp = entry.get("SaveParameter", {}).get("value", {})
    if not isinstance(sp, dict):
        return 0

    added = 0

    if "bIsAwakening" not in sp:
        sp["bIsAwakening"] = {"id": None, "value": False, "type": "BoolProperty"}
        added += 1

    if "bIsExcludedFromTeamMission" not in sp:
        sp["bIsExcludedFromTeamMission"] = {"id": None, "value": False, "type": "BoolProperty"}
        added += 1

    if "ExpTableMigrationVersion" not in sp:
        sp["ExpTableMigrationVersion"] = {"id": None, "value": {"type": "None", "value": 0}, "type": "ByteProperty"}
        added += 1

    if "FoodWithFullStomachKeep" not in sp:
        sp["FoodWithFullStomachKeep"] = {"id": None, "value": "None", "type": "NameProperty"}
        added += 1

    if "PartnerSkillCoolDownTimeMax" not in sp:
        sp["PartnerSkillCoolDownTimeMax"] = {"id": None, "value": 0.0, "type": "FloatProperty"}
        added += 1

    if "PartnerSkillLastUsedTime" not in sp:
        sp["PartnerSkillLastUsedTime"] = {"struct_type": "DateTime", "struct_id": "00000000-0000-0000-0000-000000000000", "id": None, "value": 0, "type": "StructProperty"}
        added += 1

    if "Tiemr_FoodWithFullStomachKeep" not in sp:
        sp["Tiemr_FoodWithFullStomachKeep"] = {"id": None, "value": 0, "type": "IntProperty"}
        added += 1

    if "WorkSuitabilityOverflowGrantedRankList" not in sp:
        sp["WorkSuitabilityOverflowGrantedRankList"] = {
            "array_type": "StructProperty",
            "id": None,
            "value": {
                "prop_name": "WorkSuitabilityOverflowGrantedRankList",
                "prop_type": "StructProperty",
                "values": [],
                "type_name": "PalWorkSuitabilityOverflowGrantedInfo",
                "id": "00000000-0000-0000-0000-000000000000"
            },
            "type": "ArrayProperty"
        }
        added += 1

    return added


def main():
    parser = argparse.ArgumentParser(
        description="Convert _dps.sav from old Palworld format to v1.0 format.",
    )
    parser.add_argument("dps_path", help="Path to the _dps.sav file to convert")
    args = parser.parse_args()

    if not os.path.exists(args.dps_path):
        print(f"ERROR: File not found: {args.dps_path}")
        sys.exit(1)

    print(f"Reading {args.dps_path}...")
    with open(args.dps_path, "rb") as f:
        data = f.read()

    raw, save_type, magic = decompress(data)
    gvas = GvasFile.read(raw, PALWORLD_TYPE_HINTS, CUSTOM_PROPS, allow_nan=True)
    pj = gvas.dump()

    entries = pj["properties"]["SaveParameterArray"]["value"]["values"]
    print(f"Found {len(entries)} Pal entries.")

    total_added = 0
    entries_modified = 0
    for entry in entries:
        added = add_v1_fields(entry)
        if added > 0:
            total_added += added
            entries_modified += 1

    if total_added == 0:
        print("File is already in v1.0 format. No changes needed.")
        return

    print(f"Added {total_added} fields across {entries_modified} entries.")

    print(f"Writing converted file...")
    fixed_gvas = GvasFile.load(pj)
    raw_bytes = fixed_gvas.write(CUSTOM_PROPS)
    output = compress(raw_bytes, save_type, magic)

    with open(args.dps_path, "wb") as f:
        f.write(output)

    print(f"Done. File converted to v1.0 format: {args.dps_path}")


if __name__ == "__main__":
    main()
