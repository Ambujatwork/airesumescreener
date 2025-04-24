import unittest
from src.main import app  # Assuming 'app' is the main application object

class TestMain(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_page(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Welcome to the Resume Screener', response.data)

    def test_invalid_route(self):
        response = self.app.get('/invalid')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()