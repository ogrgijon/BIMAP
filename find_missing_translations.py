import re, os

pattern = re.compile(r"""t\(["'](.*?)["']\)""")
used = set()
for root, dirs, files in os.walk('src/bimap'):
    dirs[:] = [d for d in dirs if d != '__pycache__']
    for f in files:
        if f.endswith('.py'):
            txt = open(os.path.join(root, f), encoding='utf-8').read()
            for m in pattern.finditer(txt):
                used.add(m.group(1))

ns = {}
src = open('src/bimap/i18n.py', encoding='utf-8').read()
src_before_def = src.split('def t(')[0]
exec(src_before_def, ns)
defined = set(ns.get('_ES', {}).keys())

missing = sorted(used - defined)
print(f'Used t() calls: {len(used)}')
print(f'Defined in _ES: {len(defined)}')
print(f'MISSING ({len(missing)}):')
for m in missing:
    print(f'  {repr(m)}')
