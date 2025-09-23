# fmt: off
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from unity.app import get_traffic_analysis, app
from tabulate import tabulate
# fmt: on

if __name__ == "__main__":
    with app.app_context():
        print(
            tabulate(
                get_traffic_analysis(),
                headers=["Country", "City", "Unique Users",
                         "Requests", "Avg Response (ms)"],
                tablefmt="grid"
            )
        )
