# Palworld Host Save Fix (PlM Support)

Fixes the host character when moving a co-op world to a dedicated server. Works with both the old **PlZ** format and the newer **PlM** (Oodle) format that breaks all other tools.

If you've been getting this error:
```
Exception: not a compressed Palworld save, found b'PlM' instead of b'PlZ'
```
This is the fix.

> **⚠️ IMPORTANT: Do NOT use `pip install palworld-save-tools`. It will NOT work with Palworld v1.0+ saves. You MUST clone PalworldSaveTools into this folder as described in Step 4 below. If you get `EOF not reached` or `Unknown type: ByteProperty` errors, this is why.**

> **📌 If your save is from a v1.0+ server and still fails after setup:** Load your co-op save locally on the host's PC first — the game converts it to the current format. Then run this tool on the converted files. See troubleshooting section for full steps.

---

## Quick Overview

When you move a co-op world to a dedicated server, the host loses their character. That's because co-op uses a special ID (`00000000000000000000000000000001`) that dedicated servers don't understand. This tool remaps your old character to your new server ID so you keep everything — levels, Pals, inventory, guild.

The tool fixes:
- Character data (level, stats, inventory, appearance)
- Guild membership and admin ownership
- Dimensional Pal Storage (all stored Pals become accessible again)
- Pal ownership references

---

## Step 1: Install Python

**Windows:**
1. Go to https://python.org/downloads
2. Download the latest Python (3.9 or newer)
3. Run the installer
4. **IMPORTANT:** Tick the checkbox that says "Add Python to PATH" at the bottom
5. Click "Install Now"

**Mac:**
```bash
brew install python
```

**Linux:**
```bash
sudo apt install python3 python3-pip git
```

---

## Step 2: Install Git

**Windows:**
1. Go to https://git-scm.com
2. Download and install (just click Next through everything)

**Mac/Linux:** Usually already installed. If not: `brew install git` or `sudo apt install git`

---

## Step 3: Download This Tool

Open Command Prompt (Windows) or Terminal (Mac/Linux):

```bash
cd Downloads
git clone https://github.com/NFZ-441/Palworld-Co-op-to-Dedicated-Server-Migration-Tool.git
cd Palworld-Co-op-to-Dedicated-Server-Migration-Tool
```

---

## Step 4: Install Dependencies

```bash
pip install git+https://github.com/oMaN-Rod/pyooz.git
git clone https://github.com/deafdudecomputers/PalworldSaveTools.git
```

If `pip` doesn't work, try `pip3` or `python -m pip install`.

**Your folder should look like this:**
```
Palworld-Co-op-to-Dedicated-Server-Migration-Tool/
├── fix_host_save.py
├── README.md
├── requirements.txt
├── LICENSE
└── PalworldSaveTools/       ← MUST be here (cloned in step above)
    └── src/
        └── palworld_save_tools/
```

If `PalworldSaveTools/` folder is missing, the tool will not work. Make sure you ran the `git clone` command from inside the tool folder.

---

## Step 5: Check It Works

```bash
python fix_host_save.py --help
```

You should see usage instructions. If you get an error, check the troubleshooting section below.

---

## Step 6: Upload Your Co-op Save to the Server

1. On your PC, press `Win+R` and type: `%LOCALAPPDATA%\Pal\Saved\SaveGames`
2. Open the folder with your Steam ID (a long number)
3. Find your world folder (something like `CD1538C5468F0976E17A93972F7B4E79`)
4. Upload that entire folder to your server at: `PalServer/Pal/Saved/SaveGames/0/`

Use your hosting panel's File Manager to upload. If it doesn't support folder uploads, create the folder on the server first, then upload the files inside it.

---

## Step 7: Tell the Server to Use Your Save

On the server, edit `Pal/Saved/Config/LinuxServer/GameUserSettings.ini` (or `WindowsServer` on Windows servers).

Find `DedicatedServerName=` and set it to your world folder name:
```
DedicatedServerName=CD1538C5468F0976E17A93972F7B4E79
```

Replace with your actual folder name.

---

## Step 8: Delete WorldOption.sav

Go into your uploaded save folder on the server and delete `WorldOption.sav`. This just makes players re-pick their spawn point — nothing important is lost.

---

## Step 9: Test the World

1. Start the server
2. Have a **guest** (not the host) join first
3. They'll need to create a new character — that's normal
4. Check if you can see the old bases and Pals working at the base
5. If the world looks right, continue

---

## Step 10: Host Creates a Throwaway Character

1. The **host** joins the server
2. Create any character (doesn't matter what it looks like)
3. Walk around for a few seconds
4. Leave the server

---

## Step 11: Find the New GUID

1. Stop the server
2. On the server, go to: `Pal/Saved/SaveGames/0/YOUR_WORLD/Players/`
3. Look for the **new file** that wasn't there before
4. The filename without `.sav` is the new GUID

Example: if you see `A85952B8000000000000000000000000.sav`, the GUID is `A85952B8000000000000000000000000`

Write this down.

---

## Step 12: Download the Save to Your PC

Download these from the server to a folder on your PC:
- `Level.sav`
- The entire `Players/` folder (all `.sav` files inside it, including `_dps.sav` files)

Put them in a folder **outside** the tool directory. It should look like:
```
MyFixFolder/
├── Level.sav
└── Players/
    ├── 00000000000000000000000000000001.sav
    ├── 00000000000000000000000000000001_dps.sav    ← important!
    ├── A85952B8000000000000000000000000.sav
    └── (other player files)
```

Make sure you include the `_dps.sav` files — these contain your stored Pals. Without them, Pal storage will be empty after migration.

---

## Step 13: Run the Fix

Open Command Prompt in the tool folder and run:

```bash
python fix_host_save.py "C:\Users\YOU\Downloads\MyFixFolder" A85952B8000000000000000000000000 00000000000000000000000000000001 --guild-fix
```

Replace:
- The path with where you put your downloaded save files
- `A85952B8000000000000000000000000` with the new GUID from Step 11
- Keep `00000000000000000000000000000001` as-is (that's always the old co-op host ID)
- `--guild-fix` makes sure the host stays in their guild and fixes Dimensional Pal Storage

Wait for it to finish. It'll say "Fix applied successfully" when done.

---

## Step 14: Upload the Fixed Files Back

1. Upload the fixed `Level.sav` to the server (replace the existing one)
2. Upload the fixed `Players/` folder (replace existing files)
3. Delete `00000000000000000000000000000001.sav` from Players on the server if it's still there

---

## Step 15: Start the Server

Start it up. The host joins — they should have their old character, Pals, and base access back.

---

## Step 16: Migrate Map Discovery
To restore map discovery. Each player does this on their own machine
against their own save. The map is per-client, not shared.

To fix:
1. In %LOCALAPPDATA%\Pal\Saved\SaveGames\<SteamID64>\, note your old co-op world folder <old_world_id> (sort by Date Modified if unsure)
2. Connect to the new server, let the world load and then quit cleanly. This will generate %LOCALAPPDATA%\Pal\Saved\SaveGames\<SteamID64>\<new_world_id>\LocalData.sav
4. Fully close the game(You can turn off Steam Sync, as it could re-sync and clobber the file about to be copied but it's unlikely)
5. In <new_world_id>\, rename LocalData.sav to LocalData.sav.bak, then copy <old_world_id>\LocalData.sav into <new_world_id>\
6. Relaunch the game and reconnect to the server
7. Map should be updated. Re-enabled steam sync, if you disabled it, once confirmed.

---

## After Migration — Things to Check

If the host's Pals won't fight or follow commands, drop each one from your party onto the ground and pick them back up. That fixes it.

---

## Troubleshooting

**"python" is not recognized:**
- Reinstall Python and make sure you tick "Add to PATH"
- Or try using `python3` instead of `python`

**"pip" is not recognized:**
- Try: `python -m pip install` instead of `pip install`

**"git" is not recognized:**
- Restart your terminal/command prompt after installing Git

**Windows blocks the Python installer:**
- Right-click the installer → Properties → check "Unblock" at the bottom → OK

**pyooz fails to install:**
- You need a C++ compiler. On Windows, install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

**PlM format error (with other tools):**
- Those tools are outdated. Use this tool instead — it handles PlM.

**Server keeps making a new world:**
- `DedicatedServerName` doesn't match your folder name. Check spelling and case.

**Files keep getting overwritten:**
- Stop the server before uploading/changing any files.

**Ghost player blocking guild invite:**
- Delete `00000000000000000000000000000001.sav` from the Players folder on the server.

**Can't upload folders via hosting panel:**
- Create the folder structure manually in the panel, then upload files one by one.

**Pal storage not showing:**
- Relog (leave and rejoin). If still empty, try picking up the Palbox and placing it again.

**Dimensional Pal Storage says "no data":**
- This tool fixes it automatically. Make sure you're using the latest version. Re-run the fix if you used an older version.

**Dimensional Storage stuck on "retrieving storage information":**
- This happens when the `_dps.sav` file is from an older game version than the server (e.g., co-op save from v0.6/v0.7 but server is on v1.0+). The server can't read the old format.
- To fix this, you need to let the game convert the file to the current version:
  1. On the **host's PC**, open Palworld and load the co-op save locally (just start a single player game with that save)
  2. The game will auto-convert all save data to the current version — you'll see a loading screen
  3. Once in-game, play for a few seconds, then save and exit
  4. On the host's PC, press `Win+R` and type: `%LOCALAPPDATA%\Pal\Saved\SaveGames`
  5. Open the folder with your Steam ID → then your world folder → then `Players/`
  6. Find `00000000000000000000000000000001_dps.sav` — this is now converted to the current format
  7. Copy this file to the same folder where your other save files are (where you ran the fix tool)
  8. Rename it to match the host's new server GUID: `<NEW_GUID>_dps.sav` (example: `A85952B8000000000000000000000000_dps.sav`)
  9. Run the fix tool again — it will automatically fix the GUIDs inside the DPS file:
     ```bash
     python fix_host_save.py "path/to/save" NEW_GUID 00000000000000000000000000000001 --guild-fix
     ```
  10. Upload the fixed `_dps.sav` from the Players folder to the server's Players folder
  11. Start the server, log in, and **build/place a new Dimensional Pal Storage box** at your base
  12. Open the Dimensional Storage — your Pals should appear

**Why this happens:** Palworld v1.0 added new Pal properties (like Awakening). The old `_dps.sav` file doesn't have these fields so the server can't parse it. Loading the save locally forces the game to add the missing fields. The fix tool then updates the ownership GUIDs so the server connects the data to your character.

---

## How to add Python to PATH (if you forgot)

1. Press `Win+R`, type `sysdm.cpl`, hit Enter
2. Click the **Advanced** tab
3. Click **Environment Variables**
4. Under "User variables", find **Path** and click **Edit**
5. Click **New** and add:
   ```
   C:\Users\YOUR_NAME\AppData\Local\Programs\Python\Python312\
   C:\Users\YOUR_NAME\AppData\Local\Programs\Python\Python312\Scripts\
   ```
   (Replace `YOUR_NAME` with your Windows username and `312` with your Python version)
6. Click OK everywhere
7. Open a **new** Command Prompt (old ones won't see the change)

---

## Experimental: DPS Version Converter

If you can't load the co-op save locally (e.g., the host isn't available, or you don't have the game installed), you can try converting the `_dps.sav` file directly using this script.

**When to use this:**
- Your Dimensional Storage shows "retrieving storage information" forever
- You can't load the co-op save locally to let the game convert it
- Your `_dps.sav` is from an older Palworld version (before v1.0)

**How to use:**

1. Make sure you've already set up the tool (Steps 1-4 above)
2. Run the converter on the old DPS file:
   ```bash
   python convert_dps_to_v1.py "C:\Users\YOU\Downloads\MyFixFolder\Players\00000000000000000000000000000001_dps.sav"
   ```
3. You should see: `Added XXXXX fields across XXXX entries. Done.`
4. Now run the main fix tool as normal:
   ```bash
   python fix_host_save.py "C:\Users\YOU\Downloads\MyFixFolder" NEW_GUID 00000000000000000000000000000001 --guild-fix
   ```
5. Upload the fixed files to the server
6. Build a new Dimensional Pal Storage box in-game and open it

**What it does:** Adds 8 fields that Palworld v1.0 requires (Awakening, TeamMission, etc.) with default values to every Pal entry. Your existing Pal data stays untouched.

**Warning:** This is experimental. If Dimensional Storage still doesn't work after this, use the proven method: load the co-op save locally and let the game do the conversion. Report results in the issues if you try this.

---

## Credits

Built on top of work by:
- [xNul/palworld-host-save-fix](https://github.com/xNul/palworld-host-save-fix) — original concept
- [deafdudecomputers/PalworldSaveTools](https://github.com/deafdudecomputers/PalworldSaveTools) — PlM format parsing
- [oMaN-Rod/pyooz](https://github.com/oMaN-Rod/pyooz) — Oodle decompression
- [cheahjs/palworld-save-tools](https://github.com/cheahjs/palworld-save-tools) — GVAS parsing

---

## Support

If this saved your save, consider buying me a coffee:

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-donate-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://buymeacoffee.com/nfz441)

---

MIT License
