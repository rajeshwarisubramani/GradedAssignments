import unittest

from adapters.flask_app.app import create_app


class FlaskRoutesTests(unittest.TestCase):
    def test_health_route(self):
        app = create_app()
        client = app.test_client()
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()

