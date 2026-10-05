"""Real HTTP/PostgreSQL concurrency checks; use a dedicated test database.
Set TEST_API_URL and TEST_DATABASE_URL after starting this API.
No fake database and no benchmark metrics are used by this suite.
"""

import json
import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import psycopg

BASE = os.getenv("TEST_API_URL", "http://127.0.0.1:4567").rstrip("/")
DB = os.getenv("TEST_DATABASE_URL")


def call(method, path, body=None, timeout=5):
    data = None if body is None else json.dumps(body).encode()
    req = Request(
        BASE + path,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    try:
        with urlopen(req, timeout=timeout) as response:
            raw = response.read()
            return response.status, json.loads(raw) if raw else None
    except HTTPError as err:
        raw = err.read()
        return err.code, json.loads(raw) if raw else None


@unittest.skipUnless(
    DB, "Set TEST_DATABASE_URL to run real PostgreSQL concurrency checks"
)
class ConcurrencyTests(unittest.TestCase):
    def setUp(self):
        status, self.plan = call(
            "POST",
            "/api/travel-plans",
            {"title": "Concurrency test", "description": "0"},
        )
        self.assertEqual(status, 201)
        self.pid = self.plan["id"]
        self.path = "/api/travel-plans/" + self.pid
        self.locs = []
        for i in range(4):
            status, loc = call(
                "POST", self.path + "/locations", {"name": str(i), "notes": "0"}
            )
            self.assertEqual(status, 201)
            self.locs.append(loc)

    def tearDown(self):
        call("DELETE", self.path)

    def snapshot(self):
        code, data = call("GET", self.path)
        self.assertEqual(code, 200)
        return data

    def parallel(self, requests):
        barrier = threading.Barrier(len(requests))

        def send(item):
            barrier.wait()
            return call(*item)

        with ThreadPoolExecutor(max_workers=len(requests)) as executor:
            return list(executor.map(send, requests))

    def test_location_cas_has_one_winner(self):
        loc = self.locs[0]
        path = "/api/locations/" + loc["id"]
        replies = self.parallel(
            [("PUT", path, {"notes": str(i), "version": 1}) for i in range(12)]
        )
        self.assertEqual(sorted(code for code, _ in replies), [200] + [409] * 11)
        current = self.snapshot()["locations"][0]
        self.assertEqual(current["version"], 2)
        for code, body in replies:
            if code == 409:
                self.assertEqual(body["current_version"], 2)

    def test_plan_cas_has_one_winner(self):
        replies = self.parallel(
            [("PUT", self.path, {"title": str(i), "version": 1}) for i in range(8)]
        )
        self.assertEqual(sorted(code for code, _ in replies), [200] + [409] * 7)

    def test_disjoint_reorders_share_collection_token(self):
        before = self.snapshot()
        token = before["order_version"]
        replies = self.parallel(
            [
                (
                    "PUT",
                    "/api/locations/" + self.locs[0]["id"],
                    {"visit_order": 2, "version": 1, "order_version": token},
                ),
                (
                    "PUT",
                    "/api/locations/" + self.locs[3]["id"],
                    {"visit_order": 3, "version": 1, "order_version": token},
                ),
            ]
        )
        self.assertEqual(sorted(code for code, _ in replies), [200, 409])
        rejected = [body for code, body in replies if code == 409][0]
        self.assertEqual(rejected["current_order_version"], token + 1)
        after = self.snapshot()
        self.assertEqual(after["order_version"], token + 1)
        self.assertEqual([x["visit_order"] for x in after["locations"]], [1, 2, 3, 4])

    def test_notes_does_not_lock_parent(self):
        token = self.snapshot()["order_version"]
        with psycopg.connect(DB) as conn:
            conn.execute(
                "SELECT id FROM travel_plans WHERE id=%s FOR UPDATE", (self.pid,)
            )
            with ThreadPoolExecutor(1) as executor:
                future = executor.submit(
                    call,
                    "PUT",
                    "/api/locations/" + self.locs[0]["id"],
                    {"notes": "independent", "version": 1},
                )
                code, _ = future.result(timeout=3)
                self.assertEqual(code, 200)
        after = self.snapshot()
        self.assertEqual(after["order_version"], token)
        self.assertEqual(after["version"], 1)

    def test_blocked_location_does_not_block_other_requests(self):
        # Prove one worker remains concurrent while one DB UPDATE waits.
        executor = ThreadPoolExecutor(3)
        try:
            with psycopg.connect(DB) as conn:
                conn.execute(
                    "SELECT id FROM locations WHERE id=%s FOR UPDATE",
                    (self.locs[0]["id"],),
                )
                blocked = executor.submit(
                    call,
                    "PUT",
                    "/api/locations/" + self.locs[0]["id"],
                    {"notes": "waiter", "version": 1},
                )
                # Wait for PostgreSQL to confirm a waiting UPDATE, not a timing guess.
                import time

                for _ in range(100):
                    conn.execute("SELECT pg_stat_clear_snapshot()")
                    count = conn.execute(
                        "SELECT count(*) FROM pg_stat_activity WHERE wait_event_type='Lock' AND query LIKE 'UPDATE locations SET %%'"
                    ).fetchone()[0]
                    if count:
                        break
                    time.sleep(0.02)
                self.assertGreater(count, 0, "Blocked request did not reach PostgreSQL")
                other = executor.submit(
                    call,
                    "PUT",
                    "/api/locations/" + self.locs[1]["id"],
                    {"notes": "other", "version": 1},
                )
                plan = executor.submit(
                    call, "PUT", self.path, {"title": "parallel plan", "version": 1}
                )
                self.assertEqual(other.result(timeout=3)[0], 200)
                self.assertEqual(plan.result(timeout=3)[0], 200)
                self.assertFalse(blocked.done())
            self.assertEqual(blocked.result(timeout=3)[0], 200)
        finally:
            executor.shutdown(wait=True)

    def test_single_snapshot_while_writer_commits(self):
        started = threading.Event()
        stop = threading.Event()

        def writer():
            with psycopg.connect(DB) as conn:
                started.set()
                for i in range(1, 151):
                    if stop.is_set():
                        break
                    conn.execute(
                        "UPDATE travel_plans SET description=%s WHERE id=%s",
                        (str(i), self.pid),
                    )
                    conn.execute(
                        "UPDATE locations SET notes=%s WHERE travel_plan_id=%s",
                        (str(i), self.pid),
                    )
                    conn.commit()

        with ThreadPoolExecutor(1) as executor:
            future = executor.submit(writer)
            started.wait(2)
            try:
                for _ in range(100):
                    p = self.snapshot()
                    self.assertTrue(
                        all(l["notes"] == p["description"] for l in p["locations"])
                    )
            finally:
                stop.set()
                future.result(timeout=5)

    def test_reorder_requires_collection_version(self):
        code, _ = call(
            "PUT",
            "/api/locations/" + self.locs[0]["id"],
            {"visit_order": 2, "version": 1},
        )
        self.assertEqual(code, 400)

    def test_stale_collection_after_append_is_rejected(self):
        token = self.snapshot()["order_version"]
        self.assertEqual(
            call("POST", self.path + "/locations", {"name": "extra"})[0], 201
        )
        code, body = call(
            "PUT",
            "/api/locations/" + self.locs[0]["id"],
            {"visit_order": 2, "version": 1, "order_version": token},
        )
        self.assertEqual(code, 409)
        self.assertEqual(body["current_order_version"], token + 1)

    def test_delete_compacts_order_and_changes_versions(self):
        before = self.snapshot()
        self.assertEqual(call("DELETE", "/api/locations/" + self.locs[1]["id"])[0], 204)
        after = self.snapshot()
        self.assertEqual(after["order_version"], before["order_version"] + 1)
        self.assertEqual([x["visit_order"] for x in after["locations"]], [1, 2, 3])
        self.assertEqual([x["version"] for x in after["locations"]], [1, 2, 2])

    def test_bad_reorder_rolls_back_both_versions(self):
        before = self.snapshot()
        code, _ = call(
            "PUT",
            "/api/locations/" + self.locs[0]["id"],
            {"visit_order": 9, "version": 1, "order_version": before["order_version"]},
        )
        self.assertEqual(code, 400)
        self.assertEqual(self.snapshot(), before)

    def test_stale_location_rolls_back_collection_cas(self):
        before = self.snapshot()
        loc = self.locs[0]
        self.assertEqual(
            call("PUT", "/api/locations/" + loc["id"], {"notes": "new", "version": 1})[
                0
            ],
            200,
        )
        code, _ = call(
            "PUT",
            "/api/locations/" + loc["id"],
            {"visit_order": 2, "version": 1, "order_version": before["order_version"]},
        )
        self.assertEqual(code, 409)
        self.assertEqual(self.snapshot()["order_version"], before["order_version"])


if __name__ == "__main__":
    unittest.main()
