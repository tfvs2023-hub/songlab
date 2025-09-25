from pathlib import Path

p = Path("dist/index.html")
s = p.read_text()
start = s.find("<script>")
if start != -1:
    end = s.find("</script>", start)
    if end != -1:
        new = """<script>
    // Default runtime API to the current origin. The frontend
    // build may run on different hosts; defaulting to origin
    // avoids accidental '/api/api' duplication.
    window.__SONGLAB_API_URL__ = window.__SONGLAB_API_URL__ || window.location.origin;
    console.info('SONGLAB API URL set to', window.__SONGLAB_API_URL__);
  </script>"""
        s = s[:start] + new + s[end + 9 :]
        p.write_text(s)
        print("patched_local")
    else:
        print("no_end")
else:
    print("no_start")
