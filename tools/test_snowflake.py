
def decode_snowflake(snowflake):
    twitter_epoch = 1288834974657
    timestamp_ms = (int(snowflake) >> 22) + twitter_epoch
    return timestamp_ms / 1000.0

import datetime

ids = ["2015125374263599541", "2015121934024110326", "2015121817187627407"]
for i in ids:
    ts = decode_snowflake(i)
    dt = datetime.datetime.fromtimestamp(ts)
    print(f"ID: {i} -> {dt} (Unix: {ts})")
