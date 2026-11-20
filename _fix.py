import io
p = 'C:/SZL/edge-debug/estate-cards/weaver/cards.py'
s = io.open(p, encoding='utf-8').read()
s = s.replace('"assets/org-context.svg"', '"assets/szl-card/org-context.svg"')
s = s.replace('"assets/mesh-receipts.svg"', '"assets/szl-card/mesh-receipts.svg"')
io.open(p, 'w', encoding='utf-8').write(s)
import py_compile
py_compile.compile(p, doraise=True)
print('CARDS_FIXED_COMPILED')
for f in ('charts.py', 'policy.py', 'audit.py', 'rollout_hf.py'):
    py_compile.compile('C:/SZL/edge-debug/estate-cards/weaver/' + f, doraise=True)
    print('COMPILED', f)
