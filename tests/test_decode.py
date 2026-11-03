import base64
import json
import unittest

from easy_cidaren.security.decode import debase64
from unittest.mock import patch


class DecodeTests(unittest.TestCase):
    def test_decodes_plain_json_response(self):
        payload = base64.b64encode(json.dumps({'word': 'test'}).encode( )).decode( )
        self.assertEqual(debase64(payload), {'word': 'test'})
    
    def test_invalid_json_raises(self):
        payload = base64.b64encode(b'{"broken":}').decode( )
        with self.assertRaises(ValueError):
            debase64(payload)

    def test_recovers_shuffled_chunks_including_the_remainder(self):
        original = {'word': 'test'}
        payload = base64.b64encode(json.dumps(original).encode( )).decode( )
        chunk = len(payload) // 5
        order = [3, 1, 0, 4, 2]
        scrambled = ''.join(payload[i * chunk:(i + 1) * chunk] for i in order) + payload[5 * chunk:]
        config = {'uc': [], 'avg': 5, 'loc': order}
        with patch.dict('easy_cidaren.security.decode.JV_THREE', {'3_test': config}):
            self.assertEqual(debase64(scrambled, '3_test'), original)

    def test_short_obfuscated_payload_has_a_clear_error(self):
        with self.assertRaisesRegex(ValueError, '长度不足'):
            debase64('x', '3_1021')


if __name__ == '__main__':
    unittest.main( )
