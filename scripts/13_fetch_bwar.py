from psl.data.bwar import player_season_batting_value, player_season_pitching_value

if __name__ == "__main__":
    b = player_season_batting_value()
    p = player_season_pitching_value()
    print("bwar bat player-seasons", len(b), "years", sorted(b.season.unique())[:3], "...", sorted(b.season.unique())[-1:])
    print("bwar pitch player-seasons", len(p), "years", sorted(p.season.unique())[:3], "...", sorted(p.season.unique())[-1:])
