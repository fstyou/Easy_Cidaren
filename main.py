"""Application entry point."""

import os
import sys


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == '--internal-mitmdump':
        del sys.argv[1]
        # Windows 无控制台包的标准流为 None，mitmproxy 仍需调用 isatty 等接口。
        for name, mode in (('stdin', 'r'), ('stdout', 'w'), ('stderr', 'w')):
            if getattr(sys, name) is None:
                setattr(sys, name, open(os.devnull, mode, encoding = 'utf-8'))
        from mitmproxy.tools.main import mitmdump
        
        mitmdump( )
    else:
        from easy_cidaren.app import main
        
        sys.exit(main( ))
