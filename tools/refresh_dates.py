"""Daily Workbench refresh: set each app's `updated` date and Active/Resting status from the
latest GitHub commit that touched its index.html, then rebuild the site if anything changed.

Usage (from the repo root): python3 tools/refresh_dates.py [--dry-run]
Prints CHANGED or NO CHANGE on the last line. Exits non-zero on any error, leaving files untouched.
"""
import json, os, re, subprocess, sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src', 'workbench.html')
TZ = ZoneInfo('America/New_York')
RESTING_AFTER_DAYS = 45
MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


def last_change(repo):
    url = 'https://api.github.com/repos/KrackenC/%s/commits?path=index.html&per_page=1' % repo
    cmd = ['curl', '-sSf', '--max-time', '30', '-H', 'Accept: application/vnd.github+json', '-H', 'User-Agent: workbench-refresh']
    token = os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if token:
        cmd += ['-H', 'Authorization: Bearer ' + token]
    commits = json.loads(subprocess.run(cmd + [url], check=True, capture_output=True, text=True).stdout)
    if not commits:
        raise RuntimeError('no commits touching index.html in KrackenC/' + repo)
    when = datetime.fromisoformat(commits[0]['commit']['committer']['date'].replace('Z', '+00:00'))
    return when.astimezone(TZ).date()


def main():
    dry = '--dry-run' in sys.argv
    page = open(SRC).read()
    start = page.index('var APPS = [')
    end = page.index('];', start)
    apps = page[start:end]
    today = datetime.now(TZ).date()
    changes = []

    def fix(m):
        obj = m.group(0)
        name = re.search(r'name: "([^"]+)"', obj).group(1)
        repo = re.search(r'repo: "https://github\.com/KrackenC/([^"]+)"', obj).group(1)
        old = re.search(r'updated: "(\d{4}-\d{2}-\d{2})"', obj).group(1)
        new_date = last_change(repo)
        new = new_date.isoformat()
        status = '["ok", "Active"]' if (today - new_date).days <= RESTING_AFTER_DAYS else '["idle", "Resting"]'
        obj2 = re.sub(r'updated: "\d{4}-\d{2}-\d{2}"', 'updated: "%s"' % new, obj)
        obj2 = re.sub(r'status: \[[^\]]*\]', 'status: ' + status, obj2)
        if obj2 != obj:
            changes.append('%s: %s -> %s, %s' % (name, old, new, 'Active' if 'Active' in status else 'Resting'))
        return obj2

    # each app object starts with `{ name:` and ends at the `}` that closes it (objects contain no nested `{` except `extra`)
    # apps without a repo (e.g. Shelf & Shaker, which points at its live site) keep their hand-set date
    parts = re.split(r'(?=\{ name: ")', apps)
    apps2 = ''.join(re.sub(r'\{ name: "[^"]+".*?repo: "[^"]+"(?:,\s*extra: \{[^}]*\})?\s*\}', fix, x, flags=re.S)
                    if 'repo: "https://github.com/' in x else x for x in parts)
    print('\n'.join(changes) or 'No app dates changed.')
    if not changes:
        print('NO CHANGE')
        return
    stamp = '%s %d, %d' % (MONTHS[today.month - 1], today.day, today.year)
    page2 = page[:start] + apps2 + page[end:]
    page2, n = re.subn(r'Dates refreshed [A-Z][a-z]{2} \d{1,2}, \d{4}', 'Dates refreshed ' + stamp, page2)
    assert n == 1, 'footer stamp not found'
    if dry:
        print('CHANGED (dry run, nothing written)')
        return
    open(SRC, 'w').write(page2)
    ver = str(int(json.load(open(os.path.join(ROOT, 'version.json')))['version']) + 1)
    subprocess.run([sys.executable, os.path.join(ROOT, 'build_workbench.py'), SRC, ROOT, ver], check=True)
    print('Rebuilt as version', ver)
    print('CHANGED')


if __name__ == '__main__':
    main()
