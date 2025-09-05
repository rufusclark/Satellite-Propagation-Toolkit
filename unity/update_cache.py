"""This will update the API cache every 24 hours"""

# fmt: off
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from unity.app import cache_updator, app, init_sats
import time
import datetime
# fmt: on

if __name__ == "__main__":

    with app.app_context():
        print("[API cache] Starting")
        while True:
            # clear internal CelesTrak cache to remove stale live datasets
            print("[API cache] Clearing internal SAT cache")
            init_sats.cache_clear()

            # update cache
            print("[API cache] Updating")
            cache_updator()
            print("[API Cache] Updated")

            # wait for 24 hours
            print(
                f"[API Cache] Sleeping for 15 minutes (until {datetime.datetime.now() + datetime.timedelta(minutes=15)})")
            time.sleep(60*15)
