import requests
from pathlib import Path
from datetime import datetime
import csv
import io
import re
from typing import Optional

# Define base URL and directories
BASE_URL = "https://claydavenport.com/projections"
PROJECTIONS_DIR = Path("projections")

# Define default headers for text files that might be missing them
DEFAULT_BATTING_HEADER = [
    "IDNO", "YEAR", "MLBID", "Last", "First", "Team", "Lg", "Age", "PA", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "SB", "CS", "TRND", "HBP", "BA", "OBP", "SLG", "EqBA", "EqOBP", "EqSLG", "EqA", "VORP", "WARP", "Defense", "FRAA", "MJ", "BRK", "IMP", "COL", "ATT", "DRP", "UPS", "COMP1", "COMP2", "COMP3", "COMP4", "CPW", "CSP", "CSO", "CBB", "CBA", "EQR"
]

DEFAULT_PITCHING_HEADER = [
    "HOWEID", "MLBID", "Last", "First", "Year", "Team", "Lg", "Age", "LV", "W", "L", "SV", "G", "GS", "IP", "H", "BB", "SO", "HR", "GBO%", "BABIP", "Stf", "WHIP", "RA", "ERA", "PERA", "EqERA", "EqH9", "EqBB9", "EqSO9", "EqHR9", "VORP", "--", "WARP", "Rel", "UPS", "MJ", "BRK", "IMP", "COL", "ATT", "DRP", "comp1", "comp2", "comp3", "comp4", "CSO", "CBB", "CHR", "CBA", "CDR"
]


def download_file(url: str, output_path: Path, is_space_delimited_txt: bool = False, player_type: Optional[str] = None):
    """Downloads a file, converts to CSV, standardizes header, and adds header if missing."""
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for 4xx/5xx status codes

        # Ensure the output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        text_content = response.content.decode("utf-8", errors="ignore")

        if not text_content.strip():
            # If the file is empty or just whitespace, create an empty file and return.
            output_path.touch()
            print(f"Downloaded empty file: {output_path.name}")
            return True

        if is_space_delimited_txt:
            # Process space-delimited text files
            lines = text_content.splitlines()
            rows = []
            for line in lines:
                if not line.strip():
                    continue
                row = re.split(r"\s+", line.strip())
                processed_row = [field.replace("_", " ") for field in row]
                rows.append(processed_row)

            # Check if header is missing and prepend if necessary
            if rows:
                first_cell = rows[0][0].strip()
                header_is_missing = False
                if player_type == "batting" and first_cell != "IDNO":
                    header_is_missing = True
                elif player_type == "pitching" and first_cell != "HOWEID":
                    header_is_missing = True

                if header_is_missing:
                    if player_type == "batting":
                        rows.insert(0, DEFAULT_BATTING_HEADER)
                    elif player_type == "pitching":
                        rows.insert(0, DEFAULT_PITCHING_HEADER)
        else:
            # Process standard CSV files
            rows = list(csv.reader(io.StringIO(text_content)))

        if not rows:
            output_path.touch()
            return True

        # Standardize the header by replacing 'BPID' with 'MLBID'
        header = rows[0]
        new_header = ["MLBID" if col == "BPID" else col for col in header]
        rows[0] = new_header

        # Write the processed content to the output CSV file
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"Successfully downloaded and processed: {output_path.name}")
        return True

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # It's common for some years/files to be missing, so this is not a critical error.
            print(f"File not found (404): {url}")
        else:
            print(f"Failed to download {url}: {e}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Failed to download {url}: {e}")
        return False


def download_mlb_projections():
    """
    Downloads Clay Davenport's MLB projections.
    - URL: https://claydavenport.com/projections/YYYY/clay{hitters|pitchers}[.YYYY].csv
    - Years: 2012-2025
    - Saves to: projections/davenport_mlb_YYYY_{bat|pit}.csv
    """
    print("\nDownloading Davenport MLB projections (2012-2025)...")
    end_year = 2025  # As specified

    for year in range(2012, end_year + 1):
        print(f"--- Year: {year} ---")
        # Batting
        hitter_output = PROJECTIONS_DIR / f"davenport_mlb_{year}_bat.csv"
        primary_hitter_url = f"{BASE_URL}/{year}/clayhitters.csv"
        secondary_hitter_url = f"{BASE_URL}/{year}/clayhitters.{year}.csv"

        # Try primary URL first, if it fails with a 404, try the secondary one
        if not download_file(primary_hitter_url, hitter_output):
            download_file(secondary_hitter_url, hitter_output)

        # Pitching (assuming similar naming convention and inconsistency)
        pitcher_output = PROJECTIONS_DIR / f"davenport_mlb_{year}_pit.csv"
        primary_pitcher_url = f"{BASE_URL}/{year}/claypitchers.csv"
        secondary_pitcher_url = f"{BASE_URL}/{year}/claypitchers.{year}.csv"

        if not download_file(primary_pitcher_url, pitcher_output):
            download_file(secondary_pitcher_url, pitcher_output)


def download_full_projections():
    """
    Downloads Clay Davenport's full projections.
    - URL: https://claydavenport.com/projections/YYYY/{hitter|pitcher}_projections.txt
    - Years: 2012-2025
    - Saves to: projections/davenport_full_YYYY_{bat|pit}.csv
    """
    print("\nDownloading Davenport full projections (2012-2025)...")
    end_year = 2025  # As specified

    for year in range(2012, end_year + 1):
        print(f"--- Year: {year} ---")
        # Batting
        # Based on user request, inferring hitter file name and output format
        hitter_url = f"{BASE_URL}/{year}/hitter_projections.txt"
        hitter_output = PROJECTIONS_DIR / f"davenport_full_{year}_bat.csv"
        download_file(hitter_url, hitter_output, is_space_delimited_txt=True, player_type="batting")

        # Pitching
        pitcher_url = f"{BASE_URL}/{year}/pitcher_projections.txt"
        pitcher_output = PROJECTIONS_DIR / f"davenport_full_{year}_pit.csv"
        download_file(pitcher_url, pitcher_output, is_space_delimited_txt=True, player_type="pitching")


def build_howeid_to_mlbid_map():
    """
    Builds a map from HOWEID/IDNO to MLBID from the 'full' projection files.
    These files are expected to have both an ID column (IDNO/HOWEID) and an MLBID.
    """
    print("\nBuilding HOWEID/IDNO to MLBID map...")
    howeid_map = {}
    # Iterate through the 'full' projections, which contain the ID mappings
    full_projection_files = sorted(PROJECTIONS_DIR.glob("davenport_full_*_*.csv"))

    for file_path in full_projection_files:
        print(f"  Processing for ID map: {file_path.name}")
        with open(file_path, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                continue  # Skip empty files

            # Batting files use 'IDNO', pitching files use 'HOWEID'
            id_col_name = "IDNO" if "bat" in file_path.name else "HOWEID"
            try:
                id_idx = header.index(id_col_name)
                mlbid_idx = header.index("MLBID")
            except ValueError as e:
                print(f"    Warning: Missing required column in {file_path.name}: {e}")
                continue

            for row in reader:
                if not row or len(row) <= max(id_idx, mlbid_idx):
                    continue

                howeid = row[id_idx]
                mlbid = row[mlbid_idx]

                # Skip if IDs are invalid, missing, or less than 6 digits.
                if not howeid or not mlbid or mlbid == "0" or len(mlbid) < 6:
                    continue

                # Report duplicates if a different MLBID is found for the same HOWEID
                if howeid in howeid_map and howeid_map[howeid] != mlbid:
                    print(
                        f"    Warning: Duplicate ID '{howeid}' with different MLBID. "
                        f"Existing: {howeid_map[howeid]}, New: {mlbid} (from {file_path.name}). Keeping existing."
                    )
                elif howeid not in howeid_map:
                    howeid_map[howeid] = mlbid

    print(f"ID map built. Total unique IDs found: {len(howeid_map)}")
    return howeid_map


def add_mlbid_to_mlb_projections(howeid_map: dict):
    """
    Adds or updates an MLBID column in the 'mlb' projection files using the generated ID map.
    It replaces any existing MLBID values.
    """
    print("\nAdding/Updating MLBID in MLB projections...")
    mlb_projection_files = sorted(PROJECTIONS_DIR.glob("davenport_mlb_*_*.csv"))

    for file_path in mlb_projection_files:
        print(f"  Processing for MLBID update: {file_path.name}")

        rows = []
        try:
            with open(file_path, "r", encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))
        except FileNotFoundError:
            print(f"    File not found: {file_path.name}, skipping.")
            continue

        if not rows:
            print(f"    File is empty: {file_path.name}, skipping.")
            continue

        header = rows[0]

        # Determine the primary ID column name ('IDNO' or 'HOWEID')
        id_col_name = "IDNO" if "bat" in file_path.name else "HOWEID"
        try:
            id_idx = header.index(id_col_name)
        except ValueError:
            print(f"    Warning: Cannot find ID column '{id_col_name}' in {file_path.name}. Skipping.")
            continue

        # Check for existing MLBID column
        mlbid_idx = -1
        if "MLBID" in header:
            mlbid_idx = header.index("MLBID")
            print(f"    Found existing MLBID column. Values will be replaced.")
        else:
            # If it doesn't exist, insert it after the primary ID column
            mlbid_idx = id_idx + 1
            header.insert(mlbid_idx, "MLBID")
            # For each data row, insert a placeholder to maintain row length consistency
            for row in rows[1:]:
                if len(row) >= mlbid_idx:
                    row.insert(mlbid_idx, "")  # placeholder
            print(f"    No MLBID column found. It will be added.")

        missing_ids = set()

        # Iterate over data rows to update the MLBID
        for row in rows[1:]:
            if not row or len(row) <= max(id_idx, mlbid_idx):
                continue

            howeid = row[id_idx]
            mlbid = howeid_map.get(howeid, "")

            if not mlbid and howeid:
                missing_ids.add(howeid)

            row[mlbid_idx] = mlbid

        if missing_ids:
            print(f"    Warning: Missing MLBIDs for {len(missing_ids)} IDs in {file_path.name}.")

        # Write the updated data back to the file
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

        print(f"    Successfully updated MLBID column in {file_path.name}")


if __name__ == "__main__":
    PROJECTIONS_DIR.mkdir(exist_ok=True)

    print("Starting download of Clay Davenport's projections...")

    download_mlb_projections()
    download_full_projections()

    # Build the ID map and add MLBIDs to the projections
    id_map = build_howeid_to_mlbid_map()
    add_mlbid_to_mlb_projections(id_map)

    print("\nDownload process complete.")