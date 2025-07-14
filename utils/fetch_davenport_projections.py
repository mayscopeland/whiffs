import requests
from pathlib import Path
from datetime import datetime
import csv
import io
import re
from typing import Optional, List, Dict, Tuple
import pandas as pd
from bs4 import BeautifulSoup

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

        # Remove COMP1 and all columns after it to avoid parsing issues with spaces in names
        if is_space_delimited_txt:
            rows = remove_comp_columns(rows)

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


def remove_comp_columns(rows: List[List[str]]) -> List[List[str]]:
    """
    Removes COMP1/comp1, COMP2/comp2, COMP3/comp3, COMP4/comp4 and all columns after them from the rows.
    This prevents parsing issues with spaces in player names in the comparison fields.
    """
    if not rows:
        return rows

    header = rows[0]

    # Find the index of COMP1 or comp1
    comp1_idx = -1
    for i, col in enumerate(header):
        if col == "COMP1" or col == "comp1":
            comp1_idx = i
            break

    if comp1_idx == -1:
        # No COMP1/comp1 column found, return rows as-is
        return rows

    # Keep only columns up to (but not including) COMP1/comp1
    filtered_rows = []
    for row in rows:
        filtered_row = row[:comp1_idx]
        filtered_rows.append(filtered_row)

    return filtered_rows


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

            # Determine ID column - batting files can have either 'IDNO' or 'HOWEID', pitching files use 'HOWEID'
            id_col_name = None
            id_idx = -1

            if "bat" in file_path.name:
                # For batting files, check for both IDNO and HOWEID
                if "IDNO" in header:
                    id_col_name = "IDNO"
                    id_idx = header.index("IDNO")
                elif "HOWEID" in header:
                    id_col_name = "HOWEID"
                    id_idx = header.index("HOWEID")
            else:
                # For pitching files, use HOWEID
                if "HOWEID" in header:
                    id_col_name = "HOWEID"
                    id_idx = header.index("HOWEID")

            try:
                mlbid_idx = header.index("MLBID")
            except ValueError:
                print(f"    Warning: Missing MLBID column in {file_path.name}")
                continue

            if id_col_name is None or id_idx == -1:
                print(f"    Warning: No suitable ID column found in {file_path.name}")
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

def add_mlbid_to_combined_projections(howeid_map: dict):
    """
    Adds or updates an MLBID column in the combined projection files (davenport_YYYY_bat.csv and davenport_YYYY_pit.csv).
    It replaces any existing MLBID values.
    """
    print("\nAdding/Updating MLBID in combined projections...")
    # Only target the combined projection files (not full or mlb projections)
    combined_projection_files = sorted(PROJECTIONS_DIR.glob("davenport_[0-9][0-9][0-9][0-9]_[bp][ai][at].csv"))

    for file_path in combined_projection_files:
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

        # Combined projections use HOWEID as the primary ID column
        id_col_name = "HOWEID"
        id_idx = header.index("HOWEID") if "HOWEID" in header else -1

        if id_idx == -1:
            print(f"    Warning: No HOWEID column found in {file_path.name}. Skipping.")
            continue

        # Check for existing MLBID column
        mlbid_idx = -1
        if "MLBID" in header:
            mlbid_idx = header.index("MLBID")
            print(f"    Found existing MLBID column. Values will be replaced.")
        else:
            # If it doesn't exist, insert it after the HOWEID column
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


def get_team_abbreviations(year: int) -> List[str]:
    """
    Gets all team abbreviations for a given year by scraping the year's index page.
    Returns a list of 3-letter team abbreviations.
    """
    try:
        url = f"https://claydavenport.com/projections/{year}/"
        response = requests.get(url)
        response.raise_for_status()

        # Use regex to find all links that match the pattern: 3 letters followed by .shtml
        team_links = []
        content = response.text
        # Match pattern like "WAS.shtml" - exactly 3 characters followed by .shtml
        matches = re.findall(r'href=["\']([A-Z]{3})\.shtml["\']', content)
        for match in matches:
            team_abbr = match  # The 3-letter abbreviation is the entire match
            team_links.append(team_abbr)

        # Remove duplicates and sort
        team_abbreviations = sorted(list(set(team_links)))

        # Skip OAK for 2025 (they have both ATH and OAK)
        if year == 2025 and "OAK" in team_abbreviations:
            team_abbreviations.remove("OAK")
            print(f"Removed OAK from 2025 teams (keeping ATH)")

        print(f"Found {len(team_abbreviations)} teams for {year}: {', '.join(team_abbreviations)}")
        return team_abbreviations

    except requests.exceptions.RequestException as e:
        print(f"Error fetching team list for {year}: {e}")
        return []
    except Exception as e:
        print(f"Error parsing team list for {year}: {e}")
        return []


def scrape_team_page(year: int, team_abbr: str) -> Tuple[List[List[str]], List[List[str]]]:
    """
    Scrapes a team's page to extract batting and pitching projection tables.
    Assumes the 2nd table is batters and the 3rd table is pitchers.
    Extracts player names and HOWEIDs from links.
    Returns (batting_rows, pitching_rows) where each is a list of rows (list of strings).
    """
    try:
        url = f"https://claydavenport.com/projections/{year}/{team_abbr}.shtml"
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Find all tables on the page
        tables = soup.find_all('table')

        batting_rows = []
        pitching_rows = []

        # Check if we have enough tables
        if len(tables) < 3:
            print(f"  {team_abbr}: Not enough tables found ({len(tables)}), skipping...")
            return [], []

        # Process 2nd table (index 1) - batters
        if len(tables) > 1:
            batting_table = tables[1]
            batting_rows = extract_table_with_links(batting_table, team_abbr, "batting")

        # Process 3rd table (index 2) - pitchers
        if len(tables) > 2:
            pitching_table = tables[2]
            pitching_rows = extract_table_with_links(pitching_table, team_abbr, "pitching")

        print(f"  {team_abbr}: {len(batting_rows)-1 if batting_rows else 0} batters, {len(pitching_rows)-1 if pitching_rows else 0} pitchers")
        return batting_rows, pitching_rows

    except requests.exceptions.RequestException as e:
        print(f"  Error fetching {team_abbr}: {e}")
        return [], []
    except Exception as e:
        print(f"  Error parsing {team_abbr}: {e}")
        return [], []


def rename_columns(headers: List[str]) -> List[str]:
    """
    Renames DB to 2B and TP to 3B in the header row.
    """
    renamed_headers = []
    for header in headers:
        if header == "DB":
            renamed_headers.append("2B")
        elif header == "TP":
            renamed_headers.append("3B")
        else:
            renamed_headers.append(header)
    return renamed_headers


def calculate_er(era: str, ip: str) -> str:
    """
    Calculates ER by dividing ERA by 9 and then multiplying by IP.
    Returns the calculated ER as a string, or empty string if calculation fails.
    """
    try:
        era_float = float(era)
        ip_float = float(ip)
        er = (era_float / 9) * ip_float
        return f"{er:.1f}"
    except (ValueError, ZeroDivisionError):
        return ""


def remove_empty_rows(df: pd.DataFrame) -> pd.DataFrame:
    """
    Removes rows that are completely empty or contain only whitespace/empty values.
    Returns a DataFrame with empty rows removed.
    """
    if df.empty:
        return df

    # Create a copy to avoid modifying the original
    cleaned_df = df.copy()

    # Remove rows where all values are NaN, empty strings, or whitespace
    # For each row, check if all non-numeric columns are empty/whitespace and all numeric columns are NaN/0
    def is_empty_row(row):
        for col in row.index:
            value = row[col]
            # Check if the value is NaN, empty string, or whitespace
            if pd.isna(value) or (isinstance(value, str) and value.strip() == ""):
                continue
            # Check if numeric value is 0 (for counting stats, 0 is meaningful, so we'll keep those)
            elif pd.api.types.is_numeric_dtype(type(value)) and value == 0:
                continue
            else:
                # Found a non-empty value, so this row is not empty
                return False
        return True

    # Apply the function to identify empty rows
    empty_mask = cleaned_df.apply(is_empty_row, axis=1)

    # Remove empty rows
    cleaned_df = cleaned_df[~empty_mask]

    return cleaned_df


def extract_table_with_links(table, team_abbr: str, table_type: str) -> List[List[str]]:
    """
    Extracts table data with proper handling of linked player names and HOWEIDs.
    Skips team total rows where the player name matches the team name.
    Stops processing columns after the "WARP" column.
    For pitchers, calculates ER column.
    """
    rows = []
    header_added = False
    rows_without_links = 0  # Track rows without player links
    header_row = []  # Store the header row for reference

    for row in table.find_all('tr'):
        cells = row.find_all(['td', 'th'])
        if not cells:
            continue

        row_data = []
        player_name = ""
        warp_found = False

        for cell in cells:
            # Stop processing if we've already found the WARP column
            if warp_found:
                break

            # Check if cell contains a link
            link = cell.find('a')
            if link:
                # Extract player name from link text
                player_name = link.get_text(strip=True)
                # Extract HOWEID from href
                href = link.get('href', '')
                howeid_match = re.search(r'/([^/]+)\.shtml$', href)
                howeid = howeid_match.group(1) if howeid_match else ''

                # Skip this cell since we'll handle the link data separately
                continue
            else:
                # Regular cell content
                cell_text = cell.get_text(strip=True)
                row_data.append(cell_text)

                # Check if this is the WARP column
                if cell_text.strip().upper() == "WARP":
                    warp_found = True

        if row_data:
            # Skip the first column (empty column)
            if len(row_data) > 0:
                row_data = row_data[1:]

            # Check if this is a header row (no player link, contains typical header text)
            is_header_row = False
            if not player_name and row_data:
                # Check if the first few cells contain typical header text
                header_indicators = ["POS", "G", "AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "SB", "CS", "BA", "OBA", "SLG", "EQA", "EQR", "WARP"]
                first_cell = row_data[0].strip().upper() if row_data else ""
                if first_cell in header_indicators:
                    is_header_row = True

            if is_header_row:
                # This is a header row
                header_row = ["HOWEID", "Name", "Team"]
                # Add the rest of the headers, but skip any that are already in our base header
                if len(row_data) > 0:
                    existing_headers = set(["HOWEID", "Name", "Team"])
                    for header in row_data:
                        if header not in existing_headers:
                            header_row.append(header)
                            existing_headers.add(header)
                header_row = rename_columns(header_row)

                # For pitchers, add ER column after ERA
                if table_type == "pitching":
                    era_index = -1
                    for i, header in enumerate(header_row):
                        if header.upper() == "ERA":
                            era_index = i
                            break
                    if era_index != -1:
                        header_row.insert(era_index + 1, "ER")

                rows.append(header_row)
                header_added = True
            elif player_name and len(row_data) > 0:
                # This is a data row with player information
                # Skip team total rows where player name matches team name
                if player_name.upper() == team_abbr.upper():
                    continue

                # Create new row with HOWEID first, then Name, then Team, then rest
                new_row = [howeid, player_name, team_abbr]
                new_row.extend(row_data)

                # For batting, ensure we only include columns up to WARP
                if table_type == "batting" and header_added:
                    # Find the index of WARP in the header
                    warp_index = -1
                    for i, header in enumerate(header_row):
                        if header.upper() == "WARP":
                            warp_index = i
                            break

                    # Truncate the row to only include columns up to WARP
                    if warp_index != -1 and len(new_row) > warp_index + 1:
                        new_row = new_row[:warp_index + 1]

                # For pitchers, calculate and insert ER after ERA
                if table_type == "pitching":
                    era_index = -1
                    ip_index = -1
                    for i, header in enumerate(header_row):
                        if header.upper() == "ERA":
                            era_index = i
                        elif header.upper() == "IP":
                            ip_index = i

                    if era_index != -1 and ip_index != -1 and era_index < len(new_row) and ip_index < len(new_row):
                        era_value = new_row[era_index]
                        ip_value = new_row[ip_index]
                        er_value = calculate_er(era_value, ip_value)
                        new_row.insert(era_index + 1, er_value)

                rows.append(new_row)
            else:
                # Skip rows without player links that aren't headers (like team totals)
                rows_without_links += 1
                if rows_without_links == 2:  # Second row without player link is team totals
                    continue

    return rows


def download_team_projections():
    """
    Downloads Clay Davenport's team-by-team projections for all years.
    Scrapes individual team pages and consolidates into yearly files.
    """
    print("\nDownloading Davenport team projections (2012-2025)...")
    end_year = 2025

    for year in range(2012, end_year + 1):
        print(f"--- Year: {year} ---")

        # Get team abbreviations for this year
        team_abbreviations = get_team_abbreviations(year)
        if not team_abbreviations:
            print(f"  No teams found for {year}, skipping...")
            continue

        all_batting_rows = []
        all_pitching_rows = []
        batting_header_added = False
        pitching_header_added = False

        # Process each team
        for team_abbr in team_abbreviations:
            batting_rows, pitching_rows = scrape_team_page(year, team_abbr)

            # Add batting data
            if batting_rows:
                if not batting_header_added:
                    # Add header row
                    all_batting_rows.append(batting_rows[0])
                    batting_header_added = True
                # Add data rows (skip header)
                all_batting_rows.extend(batting_rows[1:])

            # Add pitching data
            if pitching_rows:
                if not pitching_header_added:
                    # Add header row
                    all_pitching_rows.append(pitching_rows[0])
                    pitching_header_added = True
                # Add data rows (skip header)
                all_pitching_rows.extend(pitching_rows[1:])

        # Save batting file
        if all_batting_rows:
            # Remove duplicate rows based on HOWEID
            header = all_batting_rows[0]
            data_rows = all_batting_rows[1:]
            unique_rows = [header]  # Keep header
            seen_howeids = set()

            for row in data_rows:
                if len(row) > 0:
                    howeid = row[0]  # HOWEID is the first column
                    if howeid not in seen_howeids:
                        unique_rows.append(row)
                        seen_howeids.add(howeid)
                    else:
                        print(f"    Skipping duplicate player: {row[1] if len(row) > 1 else 'Unknown'} (HOWEID: {howeid})")

            batting_output = PROJECTIONS_DIR / f"davenport_team_{year}_bat.csv"
            with open(batting_output, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(unique_rows)
            print(f"  Saved {len(unique_rows)-1} batting projections to {batting_output.name} (removed {len(data_rows) - len(unique_rows) + 1} duplicates)")

        # Save pitching file
        if all_pitching_rows:
            # Remove duplicate rows based on HOWEID
            header = all_pitching_rows[0]
            data_rows = all_pitching_rows[1:]
            unique_rows = [header]  # Keep header
            seen_howeids = set()

            for row in data_rows:
                if len(row) > 0:
                    howeid = row[0]  # HOWEID is the first column
                    if howeid not in seen_howeids:
                        unique_rows.append(row)
                        seen_howeids.add(howeid)
                    else:
                        print(f"    Skipping duplicate player: {row[1] if len(row) > 1 else 'Unknown'} (HOWEID: {howeid})")

            pitching_output = PROJECTIONS_DIR / f"davenport_team_{year}_pit.csv"
            with open(pitching_output, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerows(unique_rows)
            print(f"  Saved {len(unique_rows)-1} pitching projections to {pitching_output.name} (removed {len(data_rows) - len(unique_rows) + 1} duplicates)")


def scale_projections_to_one_pa_or_bf(df: pd.DataFrame, player_type: str) -> pd.DataFrame:
    """
    Scales all counting stats in the projections to 1 PA (for batters) or 1 BF (for pitchers).

    Args:
        df: DataFrame containing the projections
        player_type: "batting" or "pitching"

    Returns:
        DataFrame with scaled projections
    """
    if df.empty:
        return df

    # Create a copy to avoid modifying the original
    scaled_df = df.copy()

    if player_type == "batting":
        # For batters, scale to 1 PA
        if "PA" not in scaled_df.columns:
            print("    Warning: No PA column found for batting projections, cannot scale")
            return scaled_df

        # Convert PA to numeric, handling any non-numeric values
        scaled_df["PA"] = pd.to_numeric(scaled_df["PA"], errors="coerce")

        # Filter out rows with invalid or zero PA
        valid_pa_mask = (scaled_df["PA"] > 0) & (scaled_df["PA"].notna())
        scaled_df = scaled_df[valid_pa_mask].copy()

        if scaled_df.empty:
            print("    Warning: No valid PA values found for scaling")
            return scaled_df

        # Calculate scaling factor (1 / PA)
        scaling_factor = 1.0 / scaled_df["PA"]

        # Scale all counting stats
        counting_stats = ["AB", "R", "H", "2B", "3B", "HR", "RBI", "BB", "SO", "SB", "CS", "HBP"]

        for stat in counting_stats:
            if stat in scaled_df.columns:
                scaled_df[stat] = pd.to_numeric(scaled_df[stat], errors="coerce").fillna(0)
                scaled_df[stat] = scaled_df[stat] * scaling_factor

        # Set PA to 1 for all scaled players
        scaled_df["PA"] = 1.0

        print(f"    Scaled {len(scaled_df)} batting projections to 1 PA each")

    elif player_type == "pitching":
        # For pitchers, scale to 1 BF (Batters Faced)
        # BF = IP * 3 + BB + H (approximation)
        if "IP" not in scaled_df.columns:
            print("    Warning: No IP column found for pitching projections, cannot scale")
            return scaled_df

        # Convert IP to numeric, handling any non-numeric values
        scaled_df["IP"] = pd.to_numeric(scaled_df["IP"], errors="coerce")

        # Filter out rows with invalid or zero IP
        valid_ip_mask = (scaled_df["IP"] > 0) & (scaled_df["IP"].notna())
        scaled_df = scaled_df[valid_ip_mask].copy()

        if scaled_df.empty:
            print("    Warning: No valid IP values found for scaling")
            return scaled_df

        # Calculate BF (Batters Faced) for each pitcher
        # BF = IP * 3 + BB + H (approximation)
        bb = pd.to_numeric(scaled_df.get("BB", 0), errors="coerce").fillna(0)
        h = pd.to_numeric(scaled_df.get("H", 0), errors="coerce").fillna(0)
        bf = scaled_df["IP"] * 3 + bb + h

        # Filter out rows with zero BF
        valid_bf_mask = bf > 0
        scaled_df = scaled_df[valid_bf_mask].copy()
        bf = bf[valid_bf_mask]

        if scaled_df.empty:
            print("    Warning: No valid BF values found for scaling")
            return scaled_df

        # Calculate scaling factor (1 / BF)
        scaling_factor = 1.0 / bf

        # Scale all counting stats
        counting_stats = ["IP", "H", "R", "HR", "BB", "SO", "W", "L", "SV"]

        for stat in counting_stats:
            if stat in scaled_df.columns:
                scaled_df[stat] = pd.to_numeric(scaled_df[stat], errors="coerce").fillna(0)
                scaled_df[stat] = scaled_df[stat] * scaling_factor

        print(f"    Scaled {len(scaled_df)} pitching projections to 1 BF each")

    return scaled_df


def combine_full_and_team_projections():
    """
    Combines full projections with team projections to create comprehensive projection files.
    For 2022, uses MLB projections instead of team projections due to bad team data.
    For other years, uses team projections as before.
    For any player who is found in the full projections but not in the base projections
    (by HOWEID, which is sometimes IDNO in the full projections), adds them to the base projection.
    Only includes columns that are found in the base projection.
    """
    print("\nCombining full projections with base projections...")
    end_year = 2025

    for year in range(2012, end_year + 1):
        print(f"--- Year: {year} ---")

        # For 2022, use MLB projections instead of team projections
        if year == 2022:
            # Process batting projections
            full_batting_file = PROJECTIONS_DIR / f"davenport_full_{year}_bat.csv"
            mlb_batting_file = PROJECTIONS_DIR / f"davenport_mlb_{year}_bat.csv"

            if full_batting_file.exists() and mlb_batting_file.exists():
                combine_projections_file(full_batting_file, mlb_batting_file, "batting", year, use_mlb=True)

            # Process pitching projections
            full_pitching_file = PROJECTIONS_DIR / f"davenport_full_{year}_pit.csv"
            mlb_pitching_file = PROJECTIONS_DIR / f"davenport_mlb_{year}_pit.csv"

            if full_pitching_file.exists() and mlb_pitching_file.exists():
                combine_projections_file(full_pitching_file, mlb_pitching_file, "pitching", year, use_mlb=True)
        else:
            # For other years, use team projections as before
            # Process batting projections
            full_batting_file = PROJECTIONS_DIR / f"davenport_full_{year}_bat.csv"
            team_batting_file = PROJECTIONS_DIR / f"davenport_team_{year}_bat.csv"

            if full_batting_file.exists() and team_batting_file.exists():
                combine_projections_file(full_batting_file, team_batting_file, "batting", year, use_mlb=False)

            # Process pitching projections
            full_pitching_file = PROJECTIONS_DIR / f"davenport_full_{year}_pit.csv"
            team_pitching_file = PROJECTIONS_DIR / f"davenport_team_{year}_pit.csv"

            if full_pitching_file.exists() and team_pitching_file.exists():
                combine_projections_file(full_pitching_file, team_pitching_file, "pitching", year, use_mlb=False)


def combine_projections_file(full_file: Path, base_file: Path, player_type: str, year: int, use_mlb: bool = False):
    """
    Combines full projections with base projections (team or MLB) to create comprehensive projection files.
    Full projections are scaled to 1 PA (batters) or 1 BF (pitchers) before combining.

    Args:
        full_file: Path to the full projections file
        base_file: Path to the base projections file (team or MLB)
        player_type: "batting" or "pitching"
        year: The year being processed
        use_mlb: Whether to use MLB projections (True) or team projections (False)
    """
    try:
        # Read full projections
        full_df = pd.read_csv(full_file)

        # Scale full projections to 1 PA or 1 BF
        print(f"  {player_type}: Scaling full projections to 1 {'PA' if player_type == 'batting' else 'BF'}...")
        scaled_full_df = scale_projections_to_one_pa_or_bf(full_df, player_type)

        # Read base projections (team or MLB)
        base_df = pd.read_csv(base_file)

        # Filter out team data rows for MLB projections (2022)
        if use_mlb:
            # Remove rows where Last column contains "TEAM" (team totals)
            if "First" in base_df.columns:
                original_count = len(base_df)
                base_df = base_df[~base_df["First"].str.contains("TEAM", case=False, na=False)]
                filtered_count = len(base_df)
                if original_count != filtered_count:
                    print(f"  {player_type}: Filtered out {original_count - filtered_count} team data rows from MLB projections")

        # Determine ID column names
        if player_type == "batting":
            # For batting, full projections can have either IDNO or HOWEID
            full_id_col = "IDNO" if "IDNO" in scaled_full_df.columns else "HOWEID"
        else:
            # For pitching, full projections use HOWEID
            full_id_col = "HOWEID"

        # Base projections use HOWEID for both MLB and team projections
        base_id_col = "HOWEID"
        if use_mlb:
            print(f"  {player_type}: Using MLB projections with HOWEID as primary ID")
            # For MLB projections, create Name column from Last and First if they exist
            if "Last" in base_df.columns and "First" in base_df.columns:
                base_df["Name"] = base_df["First"].fillna("") + " " + base_df["Last"].fillna("")
                base_df["Name"] = base_df["Name"].str.strip()
        else:
            print(f"  {player_type}: Using team projections with HOWEID as primary ID")

        # Get existing IDs in base projections
        existing_ids = set(base_df[base_id_col].astype(str))
        print(f"  {player_type}: Base projections have {len(existing_ids)} unique {base_id_col}s")
        print(f"  {player_type}: Full projections have {len(scaled_full_df)} rows after scaling")

                # For both MLB and team projections, use HOWEID directly
        missing_players = scaled_full_df[~scaled_full_df[full_id_col].astype(str).isin(existing_ids)]

        if missing_players.empty:
            print(f"  {player_type}: No missing players found")
            # Even if no missing players, we should still create the combined file with base projections
            # Remove empty rows from base projections
            original_count = len(base_df)
            cleaned_base_df = remove_empty_rows(base_df)
            final_count = len(cleaned_base_df)

            if original_count != final_count:
                print(f"  {player_type}: Removed {original_count - final_count} empty rows from base projections")

            combined_file = PROJECTIONS_DIR / f"davenport_{year}_{'bat' if player_type == 'batting' else 'pit'}.csv"
            cleaned_base_df.to_csv(combined_file, index=False)
            print(f"  {player_type}: Created combined file with base projections only")
            return

        print(f"  {player_type}: Found {len(missing_players)} missing players")

        # Debug: Print some info about the missing players
        if len(missing_players) > 0:
            print(f"  {player_type}: Sample missing players:")
            for i, (_, player) in enumerate(missing_players.head(3).iterrows()):
                last_name = player.get("Last", "Unknown")
                first_name = player.get("First", "")
                howeid = player.get(full_id_col, "None")
                print(f"    {i+1}. {first_name} {last_name} ({full_id_col}: {howeid})")

        # Map columns from full projections to base projections
        # Column structures differ between MLB and team projections
        column_mapping = {}

        if player_type == "batting":
            if use_mlb:
                # MLB batting projections typically have: HOWEID, Last, First, Team, Lg, Age, PA, AB, R, H, 2B, 3B, HR, RBI, BB, SO, SB, CS, BA, OBP, SLG, etc.
                column_mapping = {
                    full_id_col: "HOWEID",
                    "Last": "Last",
                    "First": "First",
                    "Team": "Team",
                    "PA": "PA",
                    "AB": "AB",
                    "R": "R",
                    "H": "H",
                    "2B": "2B",
                    "3B": "3B",
                    "HR": "HR",
                    "RBI": "RBI",
                    "BB": "BB",
                    "SO": "SO",
                    "SB": "SB",
                    "CS": "CS",
                    "BA": "BA",
                    "OBP": "OBP",
                    "SLG": "SLG",
                }
            else:
                # Team batting projections have: HOWEID, Name, Team, Pos, G, AB, R, H, 2B, 3B, HR, RBI, BB, SO, SB, CS, BA, OBP, SLG, etc.
                column_mapping = {
                    full_id_col: "HOWEID",
                    "Team": "Team",
                    "G": "G",
                    "AB": "AB",
                    "R": "R",
                    "H": "H",
                    "2B": "2B",
                    "3B": "3B",
                    "HR": "HR",
                    "RBI": "RBI",
                    "BB": "BB",
                    "SO": "SO",
                    "SB": "SB",
                    "CS": "CS",
                    "BA": "BA",
                    "OBP": "OBP",
                    "SLG": "SLG",
                }
        else:
            if use_mlb:
                # MLB pitching projections typically have: HOWEID, Last, First, Team, Lg, Age, W, L, SV, G, GS, IP, H, BB, SO, HR, ERA, WHIP, etc.
                column_mapping = {
                    full_id_col: "HOWEID",
                    "Last": "Last",
                    "First": "First",
                    "Team": "Team",
                    "G": "G",
                    "GS": "GS",
                    "IP": "IP",
                    "H": "H",
                    "R": "R",
                    "HR": "HR",
                    "BB": "BB",
                    "SO": "SO",
                    "W": "W",
                    "L": "L",
                    "SV": "SV",
                    "ERA": "ERA",
                    "WHIP": "WHIP",
                }
            else:
                # Team pitching projections have: HOWEID, Name, Team, Pos, G, GS, IP, H, R, HR, BB, SO, W, L, SV, ERA, ER, WHIP, WARP
                column_mapping = {
                    full_id_col: "HOWEID",
                    "Team": "Team",
                    "G": "G",
                    "GS": "GS",
                    "IP": "IP",
                    "H": "H",
                    "R": "R",
                    "HR": "HR",
                    "BB": "BB",
                    "SO": "SO",
                    "W": "W",
                    "L": "L",
                    "SV": "SV",
                    "ERA": "ERA",
                    "WHIP": "WHIP",
                }

        # Create new rows for missing players
        new_rows = []

        for _, player in missing_players.iterrows():
            new_row = {}

            # Map columns that exist in both datasets
            for full_col, base_col in column_mapping.items():
                if full_col in player.index and base_col in base_df.columns:
                    new_row[base_col] = player[full_col]

            # Handle Name column by combining Last and First (for both MLB and team projections)
            if "Name" in base_df.columns:
                if use_mlb:
                    # For MLB projections, we have Last and First columns
                    last_name = player.get("Last", "")
                    first_name = player.get("First", "")
                    if last_name and first_name:
                        new_row["Name"] = f"{first_name} {last_name}"
                    elif last_name:
                        new_row["Name"] = last_name
                    elif first_name:
                        new_row["Name"] = first_name
                    else:
                        new_row["Name"] = ""
                else:
                    # For team projections, Name column already exists in the source data
                    new_row["Name"] = player.get("Name", "")

            # Fill in missing required columns with default values
            for col in base_df.columns:
                if col not in new_row:
                    if col == "Team":
                        new_row[col] = "FA"  # Free agent
                    elif col == "Pos" and not use_mlb:
                        new_row[col] = "P" if player_type == "pitching" else "DH"
                    elif col == "ER" and not use_mlb:
                        # Calculate ER from ERA and IP if available (team projections only)
                        if "ERA" in new_row and "IP" in new_row:
                            try:
                                era = float(new_row["ERA"])
                                ip = float(new_row["IP"])
                                er = (era / 9) * ip
                                new_row[col] = round(er, 1)
                            except (ValueError, TypeError):
                                new_row[col] = 0
                        else:
                            new_row[col] = 0
                    elif col in ["G", "GS", "IP", "H", "R", "HR", "BB", "SO", "W", "L", "SV", "AB", "SB", "2B", "3B", "RBI", "CS"]:
                        new_row[col] = 0
                    elif col in ["ERA", "WHIP", "BA", "OBP", "SLG"]:
                        new_row[col] = 0.0
                    else:
                        new_row[col] = ""

            new_rows.append(new_row)

        # Create DataFrame from new rows
        new_df = pd.DataFrame(new_rows)

        # Ensure column order matches base projections
        new_df = new_df[base_df.columns]

        # Append to base projections
        combined_df = pd.concat([base_df, new_df], ignore_index=True)

        # Remove empty rows from the combined DataFrame
        original_count = len(combined_df)
        combined_df = remove_empty_rows(combined_df)
        final_count = len(combined_df)

        if original_count != final_count:
            print(f"  {player_type}: Removed {original_count - final_count} empty rows from combined projections")

        # Save combined projections to davenport_YYYY_ file
        combined_file = PROJECTIONS_DIR / f"davenport_{year}_{'bat' if player_type == 'batting' else 'pit'}.csv"
        combined_df.to_csv(combined_file, index=False)

        print(f"  {player_type}: Added {len(new_rows)} scaled players to combined projections")

    except Exception as e:
        print(f"  Error processing {player_type} for {year}: {e}")


if __name__ == "__main__":
    PROJECTIONS_DIR.mkdir(exist_ok=True)

    print("Starting download of Clay Davenport's projections...")

    # download_mlb_projections()
    #download_full_projections()
    #download_team_projections()

    # Combine full projections with base projections (team for most years, MLB for 2022)
    combine_full_and_team_projections()

    # Build the ID map and add MLBIDs to the combined projections only
    id_map = build_howeid_to_mlbid_map()
    add_mlbid_to_combined_projections(id_map)

    print("\nDownload process complete.")