import base64
import json
import unittest

from easy_cidaren.security.decode import debase64


class DecodeTests(unittest.TestCase):
    def test_decodes_plain_json_response(self):
        payload = base64.b64encode(json.dumps({'word': 'test'}).encode( )).decode( )
        self.assertEqual(debase64(payload), {'word': 'test'})
    
    def test_invalid_json_raises(self):
        payload = base64.b64encode(b'{"broken":}').decode( )
        with self.assertRaises((json.JSONDecodeError, IndexError)):
            debase64(payload)


if __name__ == '__main__':
    unittest.main( )
