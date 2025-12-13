import unittest
import json
from auth_service import app

class TestAuthService(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_health_check(self):
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'up')
        self.assertEqual(data['service'], 'auth-service')

    def test_version_check(self):
        response = self.app.get('/version')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('version', data)

if __name__ == '__main__':
    unittest.main()
