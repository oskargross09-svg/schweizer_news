"""Print Buffer organizations, channels and the createPost input schema."""
import os
k = os.environ.get("BUFFER_API_KEY", "")
print(f"key present: {bool(k)}, length {len(k)}, has surrounding whitespace: {k != k.strip()}")
import json
from buffer import gql

def show(title, res):
    print(f"\n===== {title} =====")
    print(json.dumps(res, indent=1)[:12000])

orgs = gql("query { account { organizations { id name } } }")
show("account/organizations", orgs)
try:
    org_ids = [o["id"] for o in orgs["data"]["account"]["organizations"]]
except Exception:
    org_ids = []
for oid in org_ids:
    show(f"channels {oid}", gql("""query($o: OrganizationId!) { channels(input:{organizationId:$o}) {
        id name displayName service isQueuePaused } }""", {"o": oid}))

def type_info(name):
    return gql("""query($n: String!) { __type(name:$n) { name kind
      inputFields { name type { name kind ofType { name kind ofType { name kind } } } }
      enumValues { name } } }""", {"n": name})

seen, todo = set(), ["CreatePostInput"]
while todo:
    n = todo.pop(0)
    if n in seen: continue
    seen.add(n)
    r = type_info(n)
    t = (r.get("data") or {}).get("__type")
    if not t:
        show(f"type {n}", r); continue
    if t.get("enumValues"):
        print(f"\nENUM {n}: {[e['name'] for e in t['enumValues']]}")
        continue
    print(f"\nINPUT {n}:")
    for f in t.get("inputFields") or []:
        ty = f["type"]; chain = []
        while ty:
            chain.append(ty.get("name") or ty["kind"]); 
            if ty.get("name") and ty["kind"] in ("INPUT_OBJECT", "ENUM"): todo.append(ty["name"])
            ty = ty.get("ofType")
        print(f"   {f['name']}: {' / '.join(chain)}")
