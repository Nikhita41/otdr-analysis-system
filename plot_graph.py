import matplotlib.pyplot as plt


def plot_otdr_trace(df, major_events, minor_events, dead_zones,
                    break_count, bend_count, splice_count, connector_count):

    # -------- OTDR TRACE (Power vs Distance) --------
    plt.figure(figsize=(10, 5))
    plt.plot(df["Distance"] / 1000, df["Power"], label="Fiber Trace")

    # Event vertical lines + dots
    for event in major_events:
        plt.axvline(x=event[1], linestyle="--")
        if event[0] == "Break":
            plt.scatter(event[1], min(df["Power"]), s=80, label="Break")
        elif event[0] == "Bend":
            plt.scatter(event[1], df["Power"].mean(), s=80, label="Bend")

    for event in minor_events:
        plt.axvline(x=event[1], linestyle="--")
        if event[0] == "Splice":
            plt.scatter(event[1], df["Power"].mean(), s=80, label="Splice")
        elif event[0] == "Connector":
            plt.scatter(event[1], df["Power"].mean(), s=80, label="Connector")

    plt.xlabel("Distance (km)")
    plt.ylabel("Power (dB)")
    plt.title("OTDR Trace (Distance vs Power)")
    plt.legend()
    plt.grid(True)
    plt.show()

    # -------- CUMULATIVE LOSS --------
    plt.figure(figsize=(10, 5))
    plt.plot(df["Distance"] / 1000, df["Loss"])
    plt.xlabel("Distance (km)")
    plt.ylabel("Loss (dB)")
    plt.title("Cumulative Loss vs Distance")
    plt.grid(True)
    plt.show()

    # -------- BAR CHART (MATCHES STATISTICS) --------
    plt.figure(figsize=(6, 4))
    labels = ["Break", "Bend", "Splice", "Connector"]
    counts = [break_count, bend_count, splice_count, connector_count]

    plt.bar(labels, counts)
    plt.title("Fault Distribution")
    plt.xlabel("Fault Type")
    plt.ylabel("Count")
    plt.grid(axis='y')
    plt.show()