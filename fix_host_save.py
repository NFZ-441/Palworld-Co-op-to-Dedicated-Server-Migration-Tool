"""
Palworld Host Save Fix (PlM Format Support)
Fixes host character when migrating co-op to dedicated server.
Handles both PlZ (zlib) and PlM (Oodle) save formats.

Based on xNul/palworld-host-save-fix, with PlM support via pyooz.
"""

import os
import sys
import struct
import argparse
import shutil

# Try importing from PalworldSaveTools if available (for custom properties)
PST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "PalworldSaveTools", "src")
if os.path.exists(PST_PATH):
    sys.path.insert(0, PST_PATH)
else:
    print("ERROR: PalworldSaveTools folder not found!")
    print("You MUST clone it into this directory:")
    print("  git clone https://github.com/deafdudecomputers/PalworldSaveTools.git")
    print("")
    print("The pip version of palworld-save-tools does NOT work with Palworld v1.0 saves.")
    sys.exit(1)

from palworld_save_tools.gvas import GvasFile
from palworld_save_tools.paltypes import PALWORLD_TYPE_HINTS, PALWORLD_CUSTOM_PROPERTIES

try:
    from palworld_save_tools.paltypes import SKP_PALWORLD_CUSTOM_PROPERTIES
    CUSTOM_PROPS = SKP_PALWORLD_CUSTOM_PROPERTIES
except ImportError:
    CUSTOM_PROPS = PALWORLD_CUSTOM_PROPERTIES


def decompress_sav(data: bytes) -> tuple:
    """Decompress a Palworld .sav file. Supports PlZ and PlM formats."""
    uncompressed_len = int.from_bytes(data[0:4], byteorder="little")
    compressed_len = int.from_bytes(data[4:8], byteorder="little")
    magic = data[8:11]
    save_type = data[11]

    if magic == b"PlZ":
        import zlib
        if save_type == 0x31:
            raw = zlib.decompress(data[12:])
        elif save_type == 0x32:
            raw = zlib.decompress(zlib.decompress(data[12:]))
        else:
            raise Exception(f"Unknown PlZ save type: 0x{save_type:02X}")
        return raw, save_type

    elif magic == b"PlM":
        try:
            import ooz
        except ImportError:
            print("ERROR: PlM format requires the 'pyooz' package.")
            print("Install it with: pip install git+https://github.com/oMaN-Rod/pyooz.git")
            sys.exit(1)

        compressed_data = data[12:12 + compressed_len]
        decompressed = ooz.decompress(compressed_data, uncompressed_len)
        if len(decompressed) != uncompressed_len:
            raise Exception(
                f"Decompressed length mismatch: got {len(decompressed)}, expected {uncompressed_len}"
            )
        return decompressed, save_type

    elif magic == b"CNK":
        # Chunked format - re-read header
        import zlib
        uncompressed_len = int.from_bytes(data[12:16], byteorder="little")
        compressed_len = int.from_bytes(data[16:20], byteorder="little")
        magic2 = data[20:23]
        save_type = data[23]
        if magic2 == b"PlZ":
            raw = zlib.decompress(data[24:])
            return raw, save_type
        else:
            raise Exception(f"Unknown CNK sub-format: {magic2}")

    else:
        raise Exception(f"Unknown save format magic: {magic!r}")


def compress_sav(data: bytes, save_type: int, original_magic: bytes = b"PlM") -> bytes:
    """Compress data back to the original save format."""
    if original_magic == b"PlZ":
        import zlib
        compressed = zlib.compress(data)
        uncompressed_len = len(data)
        compressed_len = len(compressed)
        header = struct.pack("<II", uncompressed_len, compressed_len)
        header += b"PlZ"
        header += bytes([save_type])
        return header + compressed

    elif original_magic == b"PlM":
        import ooz
        uncompressed_len = len(data)
        # Mermaid compressor (9), Normal level (4)
        compressed = ooz.compress(9, 4, data, uncompressed_len)
        if not compressed:
            raise Exception("Oodle compression failed")
        compressed_len = len(compressed)
        header = struct.pack("<II", uncompressed_len, compressed_len)
        header += b"PlM"
        header += bytes([save_type])
        return header + compressed

    else:
        raise Exception(f"Cannot compress to format: {original_magic!r}")


def detect_format(filepath: str) -> bytes:
    """Detect the save file format (PlZ or PlM)."""
    with open(filepath, "rb") as f:
        header = f.read(12)
    return header[8:11]


def sav_to_json(filepath: str) -> tuple:
    """Read a .sav file and return (json_data, save_type, magic)."""
    print(f"  Converting {os.path.basename(filepath)} to JSON...", end="", flush=True)
    with open(filepath, "rb") as f:
        data = f.read()

    magic = data[8:11]
    raw_gvas, save_type = decompress_sav(data)
    gvas_file = GvasFile.read(raw_gvas, PALWORLD_TYPE_HINTS, CUSTOM_PROPS, allow_nan=True)
    print(" Done!")
    return gvas_file.dump(), save_type, magic


def json_to_sav(json_data: dict, output_filepath: str, save_type: int, magic: bytes):
    """Write JSON data back to a .sav file."""
    print(f"  Converting JSON to {os.path.basename(output_filepath)}...", end="", flush=True)
    gvas_file = GvasFile.load(json_data)
    raw_bytes = gvas_file.write(CUSTOM_PROPS)
    sav_data = compress_sav(raw_bytes, save_type, magic)
    with open(output_filepath, "wb") as f:
        f.write(sav_data)
    print(" Done!")


def format_guid(guid: str) -> str:
    """Format a 32-char GUID into the dashed format."""
    return f"{guid[:8]}-{guid[8:12]}-{guid[12:16]}-{guid[16:20]}-{guid[20:]}".lower()


def fix_host_save(save_path: str, new_guid: str, old_guid: str, guild_fix: bool = False):
    """Main fix function."""
    new_guid_formatted = format_guid(new_guid)
    old_guid_formatted = format_guid(old_guid)

    level_sav_path = os.path.join(save_path, "Level.sav")
    old_sav_path = os.path.join(save_path, "Players", f"{old_guid}.sav")
    new_sav_path = os.path.join(save_path, "Players", f"{new_guid}.sav")

    # Validate files exist
    if not os.path.exists(save_path):
        print(f"ERROR: Save path does not exist: {save_path}")
        sys.exit(1)
    if not os.path.exists(level_sav_path):
        print(f"ERROR: Level.sav not found in: {save_path}")
        sys.exit(1)
    if not os.path.exists(old_sav_path):
        print(f"ERROR: Old player save not found: {old_sav_path}")
        sys.exit(1)
    if not os.path.exists(new_sav_path):
        print(f"ERROR: New player save not found: {new_sav_path}")
        print("  Make sure the host joined the server and created a throwaway character first.")
        sys.exit(1)

    print("=" * 60)
    print("  Palworld Host Save Fix (PlM/PlZ)")
    print("=" * 60)
    print(f"  Save path:  {save_path}")
    print(f"  New GUID:   {new_guid} (host's throwaway character)")
    print(f"  Old GUID:   {old_guid} (host's original character)")
    print(f"  Guild fix:  {'Enabled' if guild_fix else 'Disabled'}")
    print("=" * 60)
    print()

    # Step 1: Convert saves to JSON
    print("[Step 1/5] Reading save files...")
    level_json, level_save_type, level_magic = sav_to_json(level_sav_path)
    old_json, old_save_type, old_magic = sav_to_json(old_sav_path)

    # Step 2: Modify player data
    print("\n[Step 2/5] Modifying player data...")
    old_json["properties"]["SaveData"]["value"]["PlayerUId"]["value"] = new_guid_formatted
    old_json["properties"]["SaveData"]["value"]["IndividualId"]["value"]["PlayerUId"]["value"] = new_guid_formatted
    old_instance_id = old_json["properties"]["SaveData"]["value"]["IndividualId"]["value"]["InstanceId"]["value"]
    print(f"  Old instance ID: {old_instance_id}")
    print("  Player UID updated.")

    # Step 3: Modify Level.sav character map
    print("\n[Step 3/5] Updating character map in Level.sav...")
    cspm = level_json["properties"]["worldSaveData"]["value"]["CharacterSaveParameterMap"]["value"]
    found = False
    for entry in cspm:
        if entry["key"]["InstanceId"]["value"] == old_instance_id:
            entry["key"]["PlayerUId"]["value"] = new_guid_formatted
            found = True
            break

    if found:
        print("  Character map entry updated.")
    else:
        print("  WARNING: Could not find character entry in Level.sav!")

    # Step 4: Guild fix
    if guild_fix:
        print("\n[Step 4/6] Applying guild fix...")
        guild_count = 0
        groups = level_json["properties"]["worldSaveData"]["value"]["GroupSaveDataMap"]["value"]
        for g in groups:
            if g["value"]["GroupType"]["value"]["value"] != "EPalGroupType::Guild":
                continue

            raw = g["value"]["RawData"]["value"]
            guild_name = raw.get("group_name", "Unknown")

            # Fix individual_character_handle_ids
            for h in raw.get("individual_character_handle_ids", []):
                if h.get("guid") == old_guid_formatted:
                    h["guid"] = new_guid_formatted
                    guild_count += 1
                if h.get("instance_id") == old_instance_id and h.get("guid") != new_guid_formatted:
                    h["guid"] = new_guid_formatted
                    guild_count += 1

            # Fix admin_player_uid
            if raw.get("admin_player_uid") == old_guid_formatted:
                raw["admin_player_uid"] = new_guid_formatted
                guild_count += 1

            # Fix players list
            for p in raw.get("players", []):
                if p.get("player_uid") == old_guid_formatted:
                    p["player_uid"] = new_guid_formatted
                    guild_count += 1

        print(f"  Updated {guild_count} guild references.")
    else:
        print("\n[Step 4/6] Skipping guild fix (disabled).")

    # Step 5: Fix Dimensional Pal Storage (InLockerCharacterInstanceIDArray)
    print("\n[Step 5/6] Fixing Dimensional Pal Storage...")
    locker_data = level_json["properties"]["worldSaveData"]["value"].get("InLockerCharacterInstanceIDArray", {}).get("value", [])
    locker_count = 0
    if locker_data:
        for entry in locker_data:
            player_uid = entry.get("PlayerUId", {}).get("value", None)
            if player_uid is not None and str(player_uid) == old_guid_formatted:
                entry["PlayerUId"]["value"] = entry["PlayerUId"]["value"].__class__.from_str(new_guid_formatted)
                locker_count += 1
        print(f"  Updated {locker_count} Pals in Dimensional Storage.")
    else:
        print("  No Dimensional Storage data found (skipping).")

    # Step 6: Fix DPS file (Dimensional Pal Storage data)
    print("\n[Step 6/7] Fixing DPS file (Pal storage data)...")
    old_dps_path = os.path.join(save_path, "Players", f"{old_guid}_dps.sav")
    new_dps_path = os.path.join(save_path, "Players", f"{new_guid}_dps.sav")
    
    if os.path.exists(old_dps_path):
        try:
            with open(old_dps_path, "rb") as f:
                dps_data = f.read()
            dps_raw, dps_save_type, dps_magic = None, None, None
            dps_magic = dps_data[8:11]
            dps_save_type = dps_data[11]
            
            if dps_magic == b"PlM":
                import ooz
                dps_ul = int.from_bytes(dps_data[0:4], byteorder="little")
                dps_cl = int.from_bytes(dps_data[4:8], byteorder="little")
                dps_raw = ooz.decompress(dps_data[12:12+dps_cl], dps_ul)
            elif dps_magic == b"PlZ":
                import zlib
                dps_raw = zlib.decompress(dps_data[12:])
            
            if dps_raw:
                gvas_dps = GvasFile.read(dps_raw, PALWORLD_TYPE_HINTS, CUSTOM_PROPS, allow_nan=True)
                dps_json = gvas_dps.dump()
                
                # Fix OwnerPlayerUId in all entries
                dps_entries = dps_json["properties"]["SaveParameterArray"]["value"]["values"]
                dps_count = 0
                for entry in dps_entries:
                    sp = entry.get("SaveParameter", {}).get("value", {})
                    if isinstance(sp, dict):
                        owner = sp.get("OwnerPlayerUId", {})
                        if isinstance(owner, dict) and old_guid_formatted in str(owner.get("value", "")).lower():
                            owner["value"] = owner["value"].__class__.from_str(new_guid_formatted)
                            dps_count += 1
                
                print(f"  Updated {dps_count} OwnerPlayerUId entries in DPS file.")
                
                # Write fixed DPS file
                fixed_dps_gvas = GvasFile.load(dps_json)
                fixed_dps_raw = fixed_dps_gvas.write(CUSTOM_PROPS)
                fixed_dps_sav = compress_sav(fixed_dps_raw, dps_save_type, dps_magic)
                
                with open(old_dps_path, "wb") as f:
                    f.write(fixed_dps_sav)
                
                # Rename DPS file to new GUID
                if os.path.exists(new_dps_path):
                    os.remove(new_dps_path)
                os.rename(old_dps_path, new_dps_path)
                print(f"  Renamed {old_guid}_dps.sav -> {new_guid}_dps.sav")
        except Exception as e:
            print(f"  WARNING: Could not fix DPS file: {e}")
            print("  You may need to load the co-op save locally to convert it to the current version.")
    else:
        print("  No DPS file found (skipping). If Dimensional Storage is empty,")
        print("  load the co-op save locally first to convert it, then copy the _dps.sav file.")

    # Step 7: Write modified saves
    print("\n[Step 7/7] Writing modified save files...")
    json_to_sav(level_json, level_sav_path, level_save_type, level_magic)
    json_to_sav(old_json, old_sav_path, old_save_type, old_magic)

    # Rename player save files
    print("\n  Renaming player files...")
    if os.path.exists(new_sav_path):
        os.remove(new_sav_path)
    os.rename(old_sav_path, new_sav_path)
    print(f"  {old_guid}.sav -> {new_guid}.sav")

    print("\n" + "=" * 60)
    print("  Fix applied successfully!")
    print("  Upload Level.sav and Players/ folder back to your server.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Fix Palworld host character when migrating co-op to dedicated server.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python fix_host_save.py ./MySave A85952B8000000000000000000000000 00000000000000000000000000000001
  python fix_host_save.py ./MySave A85952B8000000000000000000000000 00000000000000000000000000000001 --guild-fix

The old GUID for the co-op host is always: 00000000000000000000000000000001
The new GUID is the filename (without .sav) of the throwaway character created on the dedicated server.
        """,
    )
    parser.add_argument("save_path", help="Path to the save folder (containing Level.sav and Players/)")
    parser.add_argument("new_guid", help="New GUID (from throwaway character on dedicated server)")
    parser.add_argument("old_guid", help="Old GUID (always 00000000000000000000000000000001 for co-op host)")
    parser.add_argument("--guild-fix", action="store_true", help="Also fix guild membership/ownership")
    parser.add_argument("--no-backup", action="store_true", help="Skip creating a backup before modifying")

    args = parser.parse_args()

    # Validate GUIDs
    if len(args.new_guid) != 32:
        print(f"ERROR: new_guid must be 32 characters, got {len(args.new_guid)}")
        sys.exit(1)
    if len(args.old_guid) != 32:
        print(f"ERROR: old_guid must be 32 characters, got {len(args.old_guid)}")
        sys.exit(1)
    if args.new_guid == args.old_guid:
        print("ERROR: new_guid and old_guid cannot be the same!")
        sys.exit(1)
    if args.new_guid.endswith(".sav") or args.old_guid.endswith(".sav"):
        print("ERROR: Provide only the GUID, not the filename. Remove '.sav' from the end.")
        sys.exit(1)

    # Create backup
    if not args.no_backup:
        backup_path = args.save_path + "_backup"
        if not os.path.exists(backup_path):
            print(f"Creating backup at: {backup_path}")
            shutil.copytree(args.save_path, backup_path)
            print("Backup created.\n")
        else:
            print(f"Backup already exists at: {backup_path}\n")

    fix_host_save(args.save_path, args.new_guid, args.old_guid, args.guild_fix)


if __name__ == "__main__":
    main()
