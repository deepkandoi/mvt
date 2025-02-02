# Mobile Verification Toolkit (MVT)
# Copyright (c) 2021 MVT Project Developers.
# See the file 'LICENSE' for usage and copying permissions, or find a copy at
#   https://github.com/mvt-project/mvt/blob/main/LICENSE

import sqlite3
from datetime import datetime

from mvt.common.url import URL
from mvt.common.utils import convert_mactime_to_unix, convert_timestamp_to_iso

from .base import IOSExtraction

FIREFOX_HISTORY_BACKUP_IDS = [
    "2e57c396a35b0d1bcbc624725002d98bd61d142b",
]
FIREFOX_HISTORY_ROOT_PATHS = [
    "private/var/mobile/profile.profile/browser.db",
]

class FirefoxHistory(IOSExtraction):
    """This module extracts all Firefox visits and tries to detect potential
    network injection attacks."""

    def __init__(self, file_path=None, base_folder=None, output_folder=None,
                 fast_mode=False, log=None, results=[]):
        super().__init__(file_path=file_path, base_folder=base_folder,
                         output_folder=output_folder, fast_mode=fast_mode,
                         log=log, results=results)

    def serialize(self, record):
        return {
            "timestamp": record["isodate"],
            "module": self.__class__.__name__,
            "event": "firefox_history",
            "data": f"Firefox visit with ID {record['id']} to URL: {record['url']}",
        }

    def check_indicators(self):
        if not self.indicators:
            return

        for result in self.results:
            if self.indicators.check_domain(result["url"]):
                self.detected.append(result)

    def run(self):
        self._find_ios_database(backup_ids=FIREFOX_HISTORY_BACKUP_IDS, root_paths=FIREFOX_HISTORY_ROOT_PATHS)
        self.log.info("Found Firefox history database at path: %s", self.file_path)

        conn = sqlite3.connect(self.file_path)
        cur = conn.cursor()
        cur.execute("""
            SELECT
                visits.id,
                visits.date/1000000,
                history.url,
                history.title,
                visits.is_local,
                visits.type
            FROM visits, history
            WHERE visits.siteID = history.id;
        """)

        for item in cur:
            self.results.append(dict(
                id=item[0],
                isodate=convert_timestamp_to_iso(datetime.utcfromtimestamp(item[1])),
                url=item[2],
                title=item[3],
                i1000000s_local=item[4],
                type=item[5]
            ))

        cur.close()
        conn.close()

        self.log.info("Extracted a total of %d history items", len(self.results))
