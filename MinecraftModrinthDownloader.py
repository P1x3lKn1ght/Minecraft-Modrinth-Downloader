import os
import sys
import subprocess
import glob

# Auto-install 'requests' if missing
try:
    import requests
except ImportError:
    print("Installing required 'requests' library...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
        import requests
    except Exception as e:
        print(f"\n[X] Failed to install 'requests' automatically: {e}")
        print("Please install it manually by running the following command in Command Prompt: pip install requests")
        input("\nPress ENTER to exit...")
        sys.exit(1)

# Change to other loader if needed such as forge, neoforge or quilt
LOADER = "fabric"

# Base directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# List of mods to download
# For example, Fabric API at https://modrinth.com/mod/fabric-api should be written as "fabric-api" including "" with each mod split by a ","
CRITICAL_MODS = ["fabric-api","ferrite-core","lithium","chunky"]
OPTIONAL_MODS = ["clumps","axiom","worldedit","vivecraft","servux","bluemap","mob-heads","tabtps"]

API_BASE = "https://api.modrinth.com/v2"
HEADERS = {"User-Agent": "MinecraftModrinthDownloader (https://github.com/P1x3lKn1ght/Minecraft-Modrinth-Downloader)"}

def wipe_mods_directory(output_dir):
    """Deletes all existing .jar files in the folder to ensure a clean directory."""
    if not os.path.exists(output_dir):
        return

    print("\n--- Cleaning Mods Folder ---")
    existing_files = glob.glob(os.path.join(output_dir, "*.jar"))
    
    if not existing_files:
        print("  No existing .jar files found to remove.")
        return

    for file_path in existing_files:
        try:
            os.remove(file_path)
            print(f"  Deleted old mod: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"  Warning: Could not remove {os.path.basename(file_path)}: {e}")

def get_best_compatible_version(project_slug, mc_version, loader):
    url = f"{API_BASE}/project/{project_slug}/version"
    params = {
        "loaders": f'["{loader}"]',
        "game_versions": f'["{mc_version}"]'
    }
    
    try:
        response = requests.get(url, headers=HEADERS, params=params, timeout=10)
        
        if response.status_code == 404:
            print(f"  Error: Mod '{project_slug}' was not found on Modrinth.")
            return None
        elif response.status_code != 200:
            print(f"  Error: Modrinth returned status code {response.status_code}.")
            return None

        versions = response.json()
        if not versions:
            return None

        # Priority order: release, then beta, then alpha
        for target_channel in ["release", "beta", "alpha"]:
            for ver in versions:
                if ver.get("version_type") == target_channel:
                    return ver

    except requests.exceptions.ConnectionError:
        print("  Error: Could not reach Modrinth. Check your internet connection.")
    except requests.exceptions.Timeout:
        print("  Error: Request to Modrinth timed out.")
    except requests.exceptions.RequestException as e:
        print(f"  Error communicating with Modrinth: {e}")
    except ValueError:
        print("  Error: Received invalid JSON response from Modrinth.")

    return None

def download_file(url, target_path):
    try:
        response = requests.get(url, headers=HEADERS, stream=True, timeout=15)
        if response.status_code == 200:
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            print(f"    Download failed with HTTP status code {response.status_code}.")

    except requests.exceptions.ConnectionError:
        print("  Error: Could not reach server to download file.")
    except requests.exceptions.Timeout:
        print("  Error: Download request timed out.")
    except Exception as e:
        print(f"  Download error: {e}")

    return False

def process_mod_list(mod_list, is_critical, mc_version, output_dir):
    results = [] 
    category_name = "Critical" if is_critical else "Optional"
    
    print(f"\n--- Processing {category_name} Mods ---")
    
    if not mod_list:
        print("  No mods configured in this list.")
        return results
    
    for mod in mod_list:
        print(f"Checking '{mod}'...")
        version_data = get_best_compatible_version(mod, mc_version, LOADER)
        
        if not version_data:
            results.append((mod, "Not Available"))
            print(f"    - Not available for {mc_version} ({LOADER})")
            continue
            
        version_type = version_data.get("version_type", "unknown")
        primary_file = next((f for f in version_data["files"] if f.get("primary")), version_data["files"][0])
        save_path = os.path.join(output_dir, primary_file["filename"])
        
        print(f"  Downloading {primary_file['filename']} ({version_type.upper()})...")
        if download_file(primary_file["url"], save_path):
            results.append((mod, version_type))
            print(f"    - Successfully downloaded")
        else:
            results.append((mod, "Download Failed"))
            
    return results

def format_summary_section(title, results):
    section_str = f"\n{title}:\n"
    if not results:
        section_str += "  - None processed (list was empty)\n"
        return section_str

    for mod, status in results:
        if status in ["release", "beta", "alpha"]:
            section_str += f"  - {mod}: Downloaded ({status.capitalize()})\n"
        else:
            section_str += f"  - {mod}: NOT DOWNLOADED ({status})\n"
    return section_str

def main():
    print("=========================================")
    print("      Minecraft Modrinth Downloader      ")
    print("=========================================\n")

    mc_version = input("Enter the target Minecraft version (e.g., 1.20.1): ").strip()
    if not mc_version:
        print("No version entered. Exiting.")
        return

    main_version_dir = os.path.join(SCRIPT_DIR, mc_version)
    mods_dir = os.path.join(main_version_dir, mc_version)
    
    os.makedirs(mods_dir, exist_ok=True)
    print(f"Saving mods to: {mods_dir}")

    # Completely clear out all existing .jar files before fetching new ones
    wipe_mods_directory(mods_dir)

    critical_results = process_mod_list(CRITICAL_MODS, is_critical=True, mc_version=mc_version, output_dir=mods_dir)
    optional_results = process_mod_list(OPTIONAL_MODS, is_critical=False, mc_version=mc_version, output_dir=mods_dir)
        
    summary_text = "\n" + "=========================================" + "\n"
    summary_text += f"      DOWNLOAD SUMMARY FOR MC {mc_version}\n"
    summary_text += "=========================================" + "\n"
    summary_text += format_summary_section("CRITICAL MODS", critical_results)
    summary_text += format_summary_section("OPTIONAL MODS", optional_results)
    summary_text += "\n" + "========================================="

    print(summary_text)

    summary_file_path = os.path.join(main_version_dir, "Summary.txt")
    with open(summary_file_path, "w", encoding="utf-8") as f:
        f.write(summary_text.strip() + "\n")
        
    print(f"\nSummary saved to: {summary_file_path}")

if __name__ == "__main__":
    try:
        main()
    finally:
        input("\nPress ENTER to exit...")
