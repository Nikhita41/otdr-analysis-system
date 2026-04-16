import numpy as np

def merge_major_events(events, threshold=0.2):
    if not events:
        return []
    events.sort(key=lambda x: x[1])
    merged = [events[0]]

    for current in events[1:]:
        last = merged[-1]
        if abs(current[1] - last[1]) < threshold:
            if current[2] > last[2]:
                merged[-1] = current
        else:
            merged.append(current)

    return merged


def merge_minor_events(events, threshold=0.5):
    if not events:
        return []
    events.sort(key=lambda x: x[1])
    merged = [events[0]]

    for current in events[1:]:
        last = merged[-1]
        if abs(current[1] - last[1]) < threshold:
            if current[2] > last[2]:
                merged[-1] = current
        else:
            merged.append(current)

    return merged


def merge_dead_zones(dead_zones):
    if not dead_zones:
        return []
    dead_zones.sort()
    merged = [dead_zones[0]]

    for current in dead_zones[1:]:
        last = merged[-1]
        if current[0] <= last[1]:
            merged[-1] = (last[0], max(last[1], current[1]))
        else:
            merged.append(current)

    return merged


def detect_events(df):
    major_events = []
    minor_events = []
    dead_zones = []

    # -------- IMPORTANT: Distance already in KM --------
    fiber_length = df["Distance"].max()
    total_loss = df["Loss"].max() / 2

    if fiber_length > 0:
        attenuation = total_loss / fiber_length
    else:
        attenuation = 0

    for i in range(1, len(df)):
        power_drop = abs(df.loc[i, "Power_Drop"])
        reflectance = abs(df.loc[i, "Reflectance"])
        distance_km = df.loc[i, "Distance"]   # DO NOT divide again

        event_loss = abs(df.loc[i, "Loss"] - df.loc[i - 1, "Loss"])

        if event_loss < 0.5:
            continue

        if power_drop > 5:
            major_events.append(("Break", distance_km, round(event_loss, 3)))
            dead_zones.append((distance_km, distance_km + 0.05))

        elif power_drop > 3:
            major_events.append(("Bend", distance_km, round(event_loss, 3)))

        elif reflectance > 0.6 and event_loss > 1:
            minor_events.append(("Connector", distance_km, round(event_loss, 3)))
            dead_zones.append((distance_km, distance_km + 0.05))

        elif power_drop > 1 and event_loss > 0.5:
            minor_events.append(("Splice", distance_km, round(event_loss, 3)))

    major_events = merge_major_events(major_events)
    minor_events = merge_minor_events(minor_events)

    minor_events = sorted(minor_events, key=lambda x: x[2], reverse=True)
    minor_events = minor_events[:10]

    dead_zones = merge_dead_zones(dead_zones)

    bend_count = sum(1 for e in major_events if e[0] == "Bend")
    break_count = sum(1 for e in major_events if e[0] == "Break")
    splice_count = sum(1 for e in minor_events if e[0] == "Splice")
    connector_count = sum(1 for e in minor_events if e[0] == "Connector")

    return (major_events, minor_events,
            bend_count, break_count, connector_count, splice_count,
            dead_zones, fiber_length, total_loss,
            attenuation)