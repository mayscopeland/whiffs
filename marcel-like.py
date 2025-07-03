import pandas as pd
import os


def build_batting_projections(target_year, player_bio):

    hitters = player_bio[player_bio["primaryPosition"] != "P"].copy()

    year_weights = {target_year - 1: 5, target_year - 2: 4, target_year - 3: 3}
    stat_cols = [
        "G",
        "AB",
        "R",
        "H",
        "2B",
        "3B",
        "HR",
        "RBI",
        "SB",
        "CS",
        "BB",
        "SO",
        "IBB",
        "HBP",
        "SH",
        "SF",
        "GIDP",
        "PA",
    ]

    all_stats_dfs = []
    for year in year_weights.keys():
        filepath = f"stats/{year}_bat.csv"
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df["year"] = year
            all_stats_dfs.append(df)

    if not all_stats_dfs:
        return []

    total_league_stats = {col: 0 for col in stat_cols}
    for year, weight in year_weights.items():
        year_df = next((df for df in all_stats_dfs if df["year"].iloc[0] == year), None)
        if year_df is not None:
            league_year_stats = year_df[stat_cols].sum()
            if league_year_stats.get("PA", 0) > 0:
                for field in stat_cols:
                    total_league_stats[field] += league_year_stats[field] * weight

    league_avg = {}
    if total_league_stats["PA"] > 0:
        ratio = 1200 / total_league_stats["PA"]
        for field in total_league_stats:
            league_avg[field] = total_league_stats[field] * ratio

    all_stats = pd.concat(all_stats_dfs, ignore_index=True)

    pa_last_year = all_stats[all_stats["year"] == target_year - 1].set_index(
        "playerId"
    )["PA"]
    pa_two_years_ago = all_stats[all_stats["year"] == target_year - 2].set_index(
        "playerId"
    )["PA"]

    all_stats["weight"] = all_stats["year"].map(year_weights)
    for col in stat_cols:
        all_stats[f"w_{col}"] = all_stats[col].fillna(0) * all_stats["weight"]

    weighted_totals = all_stats.groupby("playerId")[
        [f"w_{col}" for col in stat_cols]
    ].sum()
    weighted_totals.columns = [c.replace("w_", "") for c in weighted_totals.columns]

    projections = weighted_totals.copy()
    for col in stat_cols:
        projections[col] += league_avg.get(col, 0)

    projections["pa_last_year"] = projections.index.map(pa_last_year).fillna(0)
    projections["pa_two_years_ago"] = projections.index.map(pa_two_years_ago).fillna(0)
    projections["projected_pa"] = (
        0.5 * projections["pa_last_year"] + 0.1 * projections["pa_two_years_ago"] + 200
    )

    projections = projections.merge(
        hitters[["playerId", "birthDate"]],
        left_index=True,
        right_on="playerId",
        how="inner",
    )
    projections["age"] = target_year - projections["birthDate"].dt.year

    age_adj = pd.Series(1.0, index=projections.index)
    age_adj.loc[projections["age"] > 29] = 1.0 + (
        (projections["age"][projections["age"] > 29] - 29) * -0.003
    )
    age_adj.loc[projections["age"] < 29] = 1.0 + (
        (29 - projections["age"][projections["age"] < 29]) * 0.006
    )
    projections["projected_pa"] *= age_adj.values

    pa_ratio = (projections["projected_pa"] / projections["PA"]).fillna(0)
    for col in stat_cols:
        projections[col] = (projections[col] * pa_ratio).round()

    projections = projections.rename(columns={"playerId": "player_id"})
    return projections[["player_id"] + stat_cols].to_dict("records")


def build_pitching_projections(target_year, player_bio):

    pitchers = player_bio[player_bio["primaryPosition"] == "P"].copy()

    year_weights = {target_year - 1: 3, target_year - 2: 2, target_year - 3: 1}
    stat_cols = [
        "G",
        "GS",
        "GF",
        "CG",
        "W",
        "L",
        "SV",
        "BS",
        "SVO",
        "HLD",
        "IP",
        "H",
        "2B",
        "3B",
        "HR",
        "R",
        "ER",
        "BB",
        "IBB",
        "SO",
        "HBP",
        "WP",
        "BK",
        "BF",
    ]

    all_stats_dfs = []
    for year in year_weights.keys():
        filepath = f"stats/{year}_pit.csv"
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            df["year"] = year
            all_stats_dfs.append(df)

    if not all_stats_dfs:
        return []

    total_league_stats = {col: 0 for col in stat_cols}
    for year, weight in year_weights.items():
        year_df = next((df for df in all_stats_dfs if df["year"].iloc[0] == year), None)
        if year_df is not None:
            league_year_stats = year_df[stat_cols].sum()
            if league_year_stats.get("BF", 0) > 0:
                for field in stat_cols:
                    total_league_stats[field] += league_year_stats[field] * weight

    league_avg = {}
    if total_league_stats.get("BF", 0) > 0:
        ratio = 1200 / total_league_stats.get("BF", 1)
        for field in total_league_stats:
            league_avg[field] = total_league_stats[field] * ratio

    all_stats = pd.concat(all_stats_dfs, ignore_index=True)

    ip_last_year = all_stats[all_stats["year"] == target_year - 1].set_index(
        "playerId"
    )["IP"]
    ip_two_years_ago = all_stats[all_stats["year"] == target_year - 2].set_index(
        "playerId"
    )["IP"]

    all_stats["weight"] = all_stats["year"].map(year_weights)
    for col in stat_cols:
        all_stats[f"w_{col}"] = all_stats[col].fillna(0) * all_stats["weight"]

    weighted_totals = all_stats.groupby("playerId")[
        [f"w_{col}" for col in stat_cols]
    ].sum()
    weighted_totals.columns = [c.replace("w_", "") for c in weighted_totals.columns]

    projections = weighted_totals.copy()
    for col in stat_cols:
        projections[col] += league_avg.get(col, 0)

    starter_ratio = (weighted_totals["GS"] / weighted_totals["G"]).fillna(0)
    ip_baseline = 25 + (starter_ratio * 35)

    projections["ip_last_year"] = projections.index.map(ip_last_year).fillna(0)
    projections["ip_two_years_ago"] = projections.index.map(ip_two_years_ago).fillna(0)
    projections["projected_ip"] = (
        0.5 * projections["ip_last_year"]
        + 0.1 * projections["ip_two_years_ago"]
        + ip_baseline
    )

    projections = projections.merge(
        pitchers[["playerId", "birthDate"]],
        left_index=True,
        right_on="playerId",
        how="inner",
    )
    projections["age"] = target_year - projections["birthDate"].dt.year

    age_adj = pd.Series(1.0, index=projections.index)
    age_adj.loc[projections["age"] > 29] = 1.0 + (
        (projections["age"][projections["age"] > 29] - 29) * -0.003
    )
    age_adj.loc[projections["age"] < 29] = 1.0 + (
        (29 - projections["age"][projections["age"] < 29]) * 0.006
    )
    projections["projected_ip"] *= age_adj.values

    ip_ratio = (projections["projected_ip"] / projections["IP"]).fillna(0)

    final_projections = projections[["playerId"]].copy()
    for col in stat_cols:
        if col != "IP":
            final_projections[col] = projections[col] * ip_ratio

    final_projections["IP"] = projections["projected_ip"]

    final_projections["IP"] = final_projections["IP"].round(1)
    for col in [c for c in stat_cols if c != "IP"]:
        final_projections[col] = final_projections[col].round()

    final_projections = final_projections.rename(columns={"playerId": "player_id"})
    # The list of columns to output
    output_cols = [
        "player_id",
        "G",
        "GS",
        "GF",
        "CG",
        "W",
        "L",
        "SV",
        "BS",
        "SVO",
        "HLD",
        "IP",
        "H",
        "2B",
        "3B",
        "HR",
        "R",
        "ER",
        "BB",
        "IBB",
        "SO",
        "HBP",
        "WP",
        "BK",
        "BF",
    ]
    return final_projections[output_cols].to_dict("records")


def main():

    os.makedirs("projections", exist_ok=True)

    player_bio = pd.read_csv("stats/player_bio.csv")
    player_bio["birthDate"] = pd.to_datetime(player_bio["birthDate"])

    for year in range(2010, 2025):
        print(f"Generating projections for {year}...")

        try:
            batting_projections = build_batting_projections(year, player_bio)
            if batting_projections:
                batting_df = pd.DataFrame(batting_projections)
                batting_filename = f"projections/marcel_{year}_bat.csv"
                batting_df.to_csv(batting_filename, index=False)
                print(
                    f"    Saved {len(batting_projections)} batting projections to {batting_filename}"
                )
            else:
                print(f"    No batting projections generated for {year}")

            pitching_projections = build_pitching_projections(year, player_bio)
            if pitching_projections:
                pitching_df = pd.DataFrame(pitching_projections)
                pitching_filename = f"projections/marcel_{year}_pit.csv"
                pitching_df.to_csv(pitching_filename, index=False)
                print(
                    f"    Saved {len(pitching_projections)} pitching projections to {pitching_filename}"
                )
            else:
                print(f"    No pitching projections generated for {year}")

        except Exception as e:
            print(f"    Error generating projections for {year}: {e}")
            import traceback

            traceback.print_exc()

    print("Projection generation complete!")


if __name__ == "__main__":
    main()
