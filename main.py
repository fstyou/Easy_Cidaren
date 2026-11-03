"""Application entry point."""

import sys


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--internal-mitmdump':
        del sys.argv[1]
        from mitmproxy.tools.main import mitmdump
        
        mitmdump( )
    else:
        from easy_cidaren.app import main
        
        sys.exit(main( ))
