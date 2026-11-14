#!/usr/bin/env bash
# Buduje raport PDF z wykonanego notebooka: nbconvert -> HTML -> PDF (headless Chrome).
set -euo pipefail
cd "$(dirname "$0")/.."
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
HTML="raport/Raport_Kamil_ZMSI.html"

jupyter nbconvert --to html Kamil_asystent.ipynb --output-dir raport --output Raport_Kamil_ZMSI.html

# Strona A4 i zawijanie długich linii kodu, żeby nic nie było ucięte w PDF.
python - "$HTML" <<'PY'
import sys
css = """<style>
@page { size: A4; margin: 12mm; }
pre, code, .highlight pre, .jp-RenderedText pre {
  white-space: pre-wrap !important; overflow-wrap: anywhere !important; word-break: break-word !important;
}
.jp-InputArea-editor, .jp-OutputArea-output, .jp-RenderedHTMLCommon { overflow: visible !important; }
table { border-collapse: collapse; font-size: 11px; }
th, td { border: 1px solid #999; padding: 3px 6px; text-align: left; }
body { padding: 0 !important; }
</style>"""
p = sys.argv[1]
s = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(s.replace("</head>", css + "</head>", 1))
PY

"$CHROME" --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=raport/Raport_Kamil_ZMSI.pdf "file://$PWD/$HTML"
rm -f "$HTML"
echo "Gotowe: raport/Raport_Kamil_ZMSI.pdf"
