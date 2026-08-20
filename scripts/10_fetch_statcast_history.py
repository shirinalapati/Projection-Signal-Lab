"""Fetch historical Statcast so Stuff+ can be scored across the modeling window."""

from psl.data.statcast_history import copy_existing_stuff_quality_seasons, fetch_years

if __name__ == "__main__":
    copy_existing_stuff_quality_seasons()
    fetch_years([2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022])
    print("statcast history fetch complete")
