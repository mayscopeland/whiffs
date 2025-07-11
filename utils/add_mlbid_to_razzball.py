#!/usr/bin/env python3
"""
Script to add MLBID columns to razzball CSV files using SFBB Player ID Map.

For each razzball_* CSV file:
- If there's a RazzID column, use it to map to MLBID
- If there's no RazzID column, extract ID from Name column URLs (/player/[id]/)
"""

import pandas as pd
import os
import glob
import re
import sys

def load_player_id_map(map_file_path):
    """Load the SFBB Player ID Map."""
    try:
        # Read the mapping file
        map_df = pd.read_csv(map_file_path)

        # Check if the required columns exist
        if 'RAZZBALLID' not in map_df.columns or 'MLBID' not in map_df.columns:
            print(f"Error: Required columns (RAZZBALLID, MLBID) not found in {map_file_path}")
            print(f"Available columns: {list(map_df.columns)}")
            return None

        # Remove rows with NaN values in key columns
        map_df = map_df.dropna(subset=['RAZZBALLID', 'MLBID'])

        # Check for duplicate RAZZBALLID values
        duplicates = map_df[map_df['RAZZBALLID'].duplicated()]
        if len(duplicates) > 0:
            print(f"Warning: Found {len(duplicates)} duplicate RAZZBALLID values, keeping first occurrence")
            map_df = map_df.drop_duplicates(subset=['RAZZBALLID'], keep='first')

        # Create a mapping dictionary
        mapping = dict(zip(map_df['RAZZBALLID'], map_df['MLBID']))
        print(f"Loaded {len(mapping)} player ID mappings")
        return mapping

    except Exception as e:
        print(f"Error loading player ID map: {e}")
        return None

def extract_id_from_url(name_value):
    """Extract ID from URL pattern /player/[id]/"""
    if pd.isna(name_value) or not isinstance(name_value, str):
        return None

    # Look for /player/[id]/ pattern
    match = re.search(r'/player/(\d+)/', name_value)
    if match:
        return int(match.group(1))
    return None

def process_razzball_csv(file_path, player_id_mapping):
    """Process a single razzball CSV file and add MLBID column."""
    try:
        # Read the CSV file
        df = pd.read_csv(file_path)
        print(f"\nProcessing {file_path}")
        print(f"Original columns: {list(df.columns)}")
        print(f"Original shape: {df.shape}")

        # Check if MLBID column already exists
        if 'MLBID' in df.columns:
            print("MLBID column already exists, will replace it...")
        else:
            print("MLBID column does not exist, will create it...")

        # Initialize MLBID column
        df['MLBID'] = None

        # Case 1: RazzID column exists
        if 'RazzID' in df.columns:
            print("Found RazzID column, using it for mapping...")

            # Clean RazzID column - remove NaN values
            valid_razzid_mask = df['RazzID'].notna()
            print(f"Valid RazzID values: {valid_razzid_mask.sum()}/{len(df)}")

            # Map RazzID to MLBID using a more robust approach
            for idx, razzid in df['RazzID'].items():
                if pd.notna(razzid) and razzid in player_id_mapping:
                    mlbid_value = player_id_mapping[razzid]
                    if pd.notna(mlbid_value):
                        df.loc[idx, 'MLBID'] = int(mlbid_value)

            mapped_count = df['MLBID'].notna().sum()
            print(f"Mapped {mapped_count}/{len(df)} players using RazzID")

        # Case 2: No RazzID column, extract from Name column
        else:
            print("No RazzID column found, extracting ID from Name column URLs...")

            if 'Name' not in df.columns:
                print("Error: No Name column found either!")
                return

            # Extract IDs from Name column URLs
            extracted_ids = df['Name'].apply(extract_id_from_url)
            extracted_count = extracted_ids.notna().sum()
            print(f"Extracted {extracted_count} IDs from URLs")

            # Map extracted IDs to MLBID using a more robust approach
            for idx, extracted_id in extracted_ids.items():
                if pd.notna(extracted_id) and extracted_id in player_id_mapping:
                    mlbid_value = player_id_mapping[extracted_id]
                    if pd.notna(mlbid_value):
                        df.loc[idx, 'MLBID'] = int(mlbid_value)

            mapped_count = df['MLBID'].notna().sum()
            print(f"Mapped {mapped_count}/{len(df)} players using extracted IDs")

        # Convert MLBID column to proper integer type (keeping NaN as NaN)
        df['MLBID'] = df['MLBID'].astype('Int64')  # Int64 allows NaN values

        # Save the updated CSV
        df.to_csv(file_path, index=False)
        print(f"Updated {file_path} with MLBID column")

    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    """Main function to process all razzball CSV files."""

    # Path to the projections directory
    projections_dir = "projections"

    # Path to the SFBB Player ID Map
    map_file_path = os.path.join(projections_dir, "SFBB Player ID Map - PLAYERIDMAP.csv")

    # Check if the map file exists
    if not os.path.exists(map_file_path):
        print(f"Error: Player ID map file not found at {map_file_path}")
        sys.exit(1)

    # Load the player ID mapping
    player_id_mapping = load_player_id_map(map_file_path)
    if player_id_mapping is None:
        print("Failed to load player ID mapping, exiting...")
        sys.exit(1)

    # Find all razzball CSV files
    pattern = os.path.join(projections_dir, "razzball_*.csv")
    razzball_files = glob.glob(pattern)

    if not razzball_files:
        print("No razzball CSV files found!")
        sys.exit(1)

    print(f"Found {len(razzball_files)} razzball CSV files:")
    for file in razzball_files:
        print(f"  - {file}")

    # Process each file
    for file_path in razzball_files:
        process_razzball_csv(file_path, player_id_mapping)

    print("\nProcessing complete!")

if __name__ == "__main__":
    main()