import os
import tempfile

from mitmproxy import http

token_file = os.environ['EASY_CIDAREN_TOKEN_FILE']

class TokenCatcher:
    def response(self, flow: http.HTTPFlow):
        if flow.request.host != "app.vocabgo.com":
            return
        
        token = flow.request.headers.get("UserToken")
        if isinstance(token, str) and token.strip( ):
            descriptor, temporary = tempfile.mkstemp(prefix = '.token-', dir = os.path.dirname(token_file))
            try:
                with os.fdopen(descriptor, 'w', encoding = 'utf-8') as stream:
                    stream.write(token.strip( ))
                os.replace(temporary, token_file)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)

addons = [TokenCatcher( )]
