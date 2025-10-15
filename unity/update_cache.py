"""This will update the API cache every 15 minutes"""

# fmt: off
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from unity.app import cache_updator, app, init_sats, CACHE_CHECK_DURATION
import time
import datetime
import traceback
# fmt: on

if __name__ == "__main__":

    with app.app_context():
        print("[API cache] Starting")
        while True:
            try:
                # clear internal CelesTrak cache to remove stale live datasets
                print("[API cache] Clearing internal SAT cache")
                init_sats.cache_clear()

                # update cache
                print("[API cache] Updating")
                cache_updator()
                print("[API Cache] Updated")

                # wait for 24 hours
                print(
                    f"[API Cache] Sleeping for {CACHE_CHECK_DURATION} minutes (until {datetime.datetime.now() + datetime.timedelta(minutes=CACHE_CHECK_DURATION)})")
                time.sleep(60*CACHE_CHECK_DURATION)

            except Exception as e:
                traceback.print_tb(e.__traceback__)
                print("Continuing...")
