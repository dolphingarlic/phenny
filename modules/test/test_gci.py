import unittest
from mock import MagicMock, patch, call
from modules import clock

class TestGCI(unittest.TestCase):
    def setUp(self):
        self.phenny = MagicMock()
        self.input = MagicMock()
