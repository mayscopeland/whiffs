import requests
import pandas as pd
import os
import time
from typing import Dict, List, Any, Set


def get_mlb_stats(season: int, group: str) -> List[Dict[str, Any]]:

    url = f"https://statsapi.mlb.com/api/v1/stats?stats=season&season={season}&group={group}&playerPool=ALL&limit=5000"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "stats" in data and len(data["stats"]) > 0:
            return data["stats"][0].get("splits", [])
        else:
            print(f"No stats found for {season} {group}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data for {season} {group}: {e}")
        return []


def extract_counting_stats_pitching(
    splits: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    records = []

    counting_stats_map = {
        "gamesPlayed": "G",
        "gamesStarted": "GS",
        "gamesFinished": "GF",
        "wins": "W",
        "losses": "L",
        "saves": "SV",
        "saveOpportunities": "SVO",
        "holds": "HLD",
        "blownSaves": "BS",
        "gamesPitched": "GP",
        "completeGames": "CG",
        "shutouts": "SHO",
        "inningsPitched": "IP",
        "hits": "H",
        "runs": "R",
        "earnedRuns": "ER",
        "homeRuns": "HR",
        "baseOnBalls": "BB",
        "intentionalWalks": "IBB",
        "strikeOuts": "SO",
        "hitBatsmen": "HBP",
        "balks": "BK",
        "wildPitches": "WP",
        "pickoffs": "PO",
        "battersFaced": "BF",
        "outs": "OUTS",
        "doubles": "2B",
        "triples": "3B",
        "sacBunts": "SH",
        "sacFlies": "SF",
        "groundOuts": "GO",
        "airOuts": "PO",
        "numberOfPitches": "PITCHES",
        "strikes": "STRIKES",
        "inheritedRunners": "IR",
        "inheritedRunnersScored": "IRS",
        "atBats": "AB",
        "stolenBases": "SB",
        "caughtStealing": "CS",
        "groundIntoDoublePlay": "GIDP",
        "catchersInterference": "CI",
        "totalBases": "TB",
    }

    for split in splits:
        if "player" in split and "stat" in split:
            record = {
                "playerId": split["player"].get("id"),
                "playerName": split["player"].get("fullName"),
                "firstName": split["player"].get("firstName"),
                "lastName": split["player"].get("lastName"),
                "teamId": split.get("team", {}).get("id"),
                "teamName": split.get("team", {}).get("name"),
                "season": split.get("season"),
                "league": split.get("league", {}).get("name"),
                "position": split.get("position", {}).get("abbreviation"),
            }

            # Add counting stats with standard abbreviations
            for api_stat, abbrev in counting_stats_map.items():
                record[abbrev] = split["stat"].get(api_stat, 0)

            records.append(record)

    return records


def extract_counting_stats_hitting(
    splits: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    records = []

    counting_stats_map = {
        "gamesPlayed": "G",
        "atBats": "AB",
        "runs": "R",
        "hits": "H",
        "doubles": "2B",
        "triples": "3B",
        "homeRuns": "HR",
        "rbi": "RBI",
        "baseOnBalls": "BB",
        "intentionalWalks": "IBB",
        "strikeOuts": "SO",
        "stolenBases": "SB",
        "caughtStealing": "CS",
        "hitByPitch": "HBP",
        "sacBunts": "SH",
        "sacFlies": "SF",
        "groundOuts": "GO",
        "airOuts": "FO",
        "groundIntoDoublePlay": "GIDP",
        "plateAppearances": "PA",
        "totalBases": "TB",
        "leftOnBase": "LOB",
        "pickoffs": "PO",
        "catchersInterference": "CI",
    }

    for split in splits:
        if "player" in split and "stat" in split:
            record = {
                "playerId": split["player"].get("id"),
                "playerName": split["player"].get("fullName"),
                "firstName": split["player"].get("firstName"),
                "lastName": split["player"].get("lastName"),
                "teamId": split.get("team", {}).get("id"),
                "teamName": split.get("team", {}).get("name"),
                "season": split.get("season"),
                "league": split.get("league", {}).get("name"),
                "position": split.get("position", {}).get("abbreviation"),
            }

            # Add counting stats with standard abbreviations
            for api_stat, abbrev in counting_stats_map.items():
                record[abbrev] = split["stat"].get(api_stat, 0)

            records.append(record)

    return records


def get_player_bio_data(player_ids: List[int]) -> List[Dict[str, Any]]:

    if not player_ids:
        return []

    # Convert player IDs to comma-separated string
    ids_str = ",".join(map(str, player_ids))
    url = f"https://statsapi.mlb.com/api/v1/people?personIds={ids_str}"

    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "people" in data:
            return data["people"]
        else:
            print(f"No people data found for player IDs: {ids_str}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching bio data for player IDs {ids_str}: {e}")
        return []


def extract_player_bio_records(
    people_data: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    records = []

    for person in people_data:
        if person.get("isPlayer", False):
            record = {
                "playerId": person.get("id"),
                "fullName": person.get("fullName", ""),
                "birthDate": person.get("birthDate", ""),
                "primaryPosition": person.get("primaryPosition", {}).get(
                    "abbreviation", ""
                ),
                "batSide": person.get("batSide", {}).get("code", ""),
                "pitchHand": person.get("pitchHand", {}).get("code", ""),
            }
            records.append(record)

    return records


def fetch_all_player_bios(unique_player_ids: Set[int]) -> None:

    print(
        f"\nFetching biographical data for {len(unique_player_ids)} unique players..."
    )

    os.makedirs("csv", exist_ok=True)

    player_ids_list = list(unique_player_ids)
    all_bio_records = []

    batch_size = 100
    total_batches = (len(player_ids_list) + batch_size - 1) // batch_size

    for i in range(0, len(player_ids_list), batch_size):
        batch_num = (i // batch_size) + 1
        batch_ids = player_ids_list[i : i + batch_size]

        print(
            f"  Processing batch {batch_num}/{total_batches} ({len(batch_ids)} players)..."
        )

        bio_data = get_player_bio_data(batch_ids)
        if bio_data:
            bio_records = extract_player_bio_records(bio_data)
            all_bio_records.extend(bio_records)
            print(f"    Retrieved {len(bio_records)} player bio records")

        # Be respectful to the API
        time.sleep(1)

    if all_bio_records:
        df_bio = pd.DataFrame(all_bio_records)
        bio_file = "stats/player_bio.csv"
        df_bio.to_csv(bio_file, index=False)
        print(f"\nSaved {len(all_bio_records)} player bio records to {bio_file}")
    else:
        print("\nNo biographical data retrieved")


def main():

    os.makedirs("stats", exist_ok=True)

    unique_player_ids: Set[int] = set()

    years = range(2007, 2025)

    for year in years:
        print(f"Fetching data for {year}...")

        print(f"  Fetching pitching stats for {year}...")
        pitching_splits = get_mlb_stats(year, "pitching")

        if pitching_splits:
            pitching_records = extract_counting_stats_pitching(pitching_splits)
            if pitching_records:
                # Collect unique player IDs
                for record in pitching_records:
                    if record.get("playerId"):
                        unique_player_ids.add(record["playerId"])

                df_pitching = pd.DataFrame(pitching_records)
                pitching_file = f"stats/{year}_pit.csv"
                df_pitching.to_csv(pitching_file, index=False)
                print(
                    f"    Saved {len(pitching_records)} pitching records to {pitching_file}"
                )
            else:
                print(f"    No pitching records found for {year}")

        print(f"  Fetching hitting stats for {year}...")
        hitting_splits = get_mlb_stats(year, "hitting")

        if hitting_splits:
            hitting_records = extract_counting_stats_hitting(hitting_splits)
            if hitting_records:
                # Collect unique player IDs
                for record in hitting_records:
                    if record.get("playerId"):
                        unique_player_ids.add(record["playerId"])

                df_hitting = pd.DataFrame(hitting_records)
                hitting_file = f"stats/{year}_bat.csv"
                df_hitting.to_csv(hitting_file, index=False)
                print(
                    f"    Saved {len(hitting_records)} hitting records to {hitting_file}"
                )
            else:
                print(f"    No hitting records found for {year}")

        # Be respectful to the API
        time.sleep(1)

    print("Data fetching complete!")

    if unique_player_ids:
        fetch_all_player_bios(unique_player_ids)
    else:
        print("No unique player IDs found to fetch biographical data")


if __name__ == "__main__":
    main()
