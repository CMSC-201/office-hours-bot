import unittest
from os import environ
from unittest import TestCase


class BotTest(TestCase):
    def test_bark(self):
        env_vars = [
            'BOT_TOKEN',
            'MONGODB_URI',
            'QUEUE_URL',
        ]
        for var in env_vars:
            self.assertTrue(var in environ)


if __name__ == '__main__':
    unittest.main()
