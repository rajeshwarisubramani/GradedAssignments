import unittest
from uuid import uuid4

from adapters.flask_app.app import create_app


class FlaskRoutesTests(unittest.TestCase):
    def test_health_route(self):
        app = create_app()
        client = app.test_client()
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)

    def test_members_route_filters_by_incomplete_name(self):
        app = create_app()
        client = app.test_client()

        member1_id = f"m-{uuid4().hex[:8]}"
        member2_id = f"m-{uuid4().hex[:8]}"
        unique_name = f"zzali_member_test_{uuid4().hex[:8]}"

        response1 = client.post(
            "/members",
            json={
                "member_id": member1_id,
                "name": unique_name,
                "email": "alice@example.com",
                "phone": "555-0001",
                "membership_date": "2024-01-15",
            },
        )
        self.assertEqual(response1.status_code, 201)

        response2 = client.post(
            "/members",
            json={
                "member_id": member2_id,
                "name": "Bob Stone",
                "email": "bob@example.com",
                "phone": "555-0002",
                "membership_date": "2024-01-16",
            },
        )
        self.assertEqual(response2.status_code, 201)

        response = client.get(f"/members?name={unique_name}")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        member_ids = {item["member_id"] for item in payload["items"]}
        self.assertIn(member1_id, member_ids)


if __name__ == "__main__":
    unittest.main()

