from psl.data.statcast_plays import harvest_statcast_plays

if __name__ == "__main__":
    counts = harvest_statcast_plays()
    print(counts)
