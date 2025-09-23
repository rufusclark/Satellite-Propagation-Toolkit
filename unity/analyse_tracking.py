# fmt: off
import os
import sys
sys.path.insert(0, os.path.abspath('.'))
sys.path.insert(0, os.path.abspath('..'))

from unity.app import get_tracking_db, app
from tabulate import tabulate
# fmt: on

if __name__ == "__main__":
    with app.app_context():
        db = get_tracking_db()
        c = db.cursor()
        c.execute("""
            SELECT city, country, COUNT(*) as hits, AVG(duration_ms) AS avg_response_ms
            FROM USAGE
            GROUP BY country, city
            ORDER BY hits DESC
        """)
        rows = c.fetchall()
        print(tabulate(rows, headers=[
              "City", "Country", "Hits", "Avg Response (ms)"], tablefmt="grid"))
