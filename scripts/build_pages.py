#!/usr/bin/env python3
import os
import glob
from jinja2 import Template

DIGEST_DIR = os.path.join(os.path.dirname(__file__), "../digests")
OUT_DIR = os.path.join(os.path.dirname(__file__), "../out")
os.makedirs(OUT_DIR, exist_ok=True)

HTML_TEMPLATE = """
<html>
<head><meta charset="utf-8"><title>Daily Digest</title></head>
<body>
<h1>Daily Paper Digest</h1>
{% for file in files %}
  <h2>{{ file.date }}</h2>
  <div>{{ file.content | safe }}</div>
{% endfor %}
</body>
</html>
"""

def main():
    files = []
    for path in sorted(glob.glob(os.path.join(DIGEST_DIR, "*.md")), reverse=True):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().replace("\n", "<br>")
        files.append({"date": os.path.basename(path)[7:-3], "content": content})

    tmpl = Template(HTML_TEMPLATE)
    html = tmpl.render(files=files)

    out_file = os.path.join(OUT_DIR, "index.html")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML page built at {out_file}")

if __name__ == "__main__":
    main()
