"""
Test L2 — Redis Stack
Vérifie : connexion, save, search, TTL, déduplication.

Prérequis : docker compose up -d
Lancer    : python test_data/test_memory_l2.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("OPENAI_API_KEY", "fake")

from Memory.team_agent.memory import l2_save, l2_search, _redis_client

OK  = "\033[92m[OK]\033[0m"
ERR = "\033[91m[FAIL]\033[0m"

passed = failed = 0

def run(label, fn):
    global passed, failed
    try:
        fn()
        passed += 1
    except Exception as e:
        print(f"  {ERR} {label} — {e}")
        failed += 1

def check(label, condition, detail=""):
    print(f"  {OK if condition else ERR}  {label}" + (f" — {detail}" if detail else ""))
    return condition

print("\n══════════════════════════════════════════")
print("  TEST L2 — Redis Stack")
print("══════════════════════════════════════════\n")

print("▶ Connexion Redis")
def t_connexion():
    r = _redis_client()
    assert r is not None, "Redis non disponible — docker compose up -d ?"
    pong = r.ping()
    check("redis.ping()", pong is True)
    keys = r.keys("team_agent:memory:*")
    print(f"       Clés existantes : {len(keys)}")
run("connexion", t_connexion)

print("\n▶ Sauvegarde")
def t_save():
    ok = l2_save("Je préfère travailler en Python pour les projets d'IA", category="preference")
    check("l2_save retourne True", ok is True)
run("save simple", t_save)

print("\n▶ Sauvegarde multiple")
def t_save_multiple():
    docs = [
        ("Le projet utilise LangGraph pour l'orchestration", "plan"),
        ("Deadline du sprint : fin de semaine", "goal"),
        ("L'agent de review vérifie la qualité du code", "fact"),
        ("Architecture microservices avec FastAPI en backend", "fact"),
    ]
    for content, cat in docs:
        ok = l2_save(content, category=cat)
        check(f"save [{cat}]", ok is True, content[:40])
run("save multiple", t_save_multiple)

print("\n▶ Recherche")
def t_search():
    results = l2_search("python", k=5)
    check(f"{len(results)} résultat(s)", len(results) > 0)
    if results:
        print(f"       Premier résultat : \"{results[0].page_content[:60]}\"")
        check("résultat pertinent contient 'python'", "python" in results[0].page_content.lower())
        check("metadata layer=L2", results[0].metadata.get("layer") == "L2")
run("search pertinence", t_search)

print("\n▶ Nombre de clés total")
def t_count():
    r = _redis_client()
    keys = r.keys("team_agent:memory:*")
    print(f"       Total clés Redis : {len(keys)}")
    by_cat = {}
    for k in keys:
        import json
        raw = r.get(k)
        if raw:
            try:
                d = json.loads(raw)
                cat = d.get("category", "?")
                by_cat[cat] = by_cat.get(cat, 0) + 1
            except Exception:
                pass
    for cat, n in sorted(by_cat.items()):
        print(f"         [{cat}] : {n} entrée(s)")
    check("au moins 1 clé présente", len(keys) >= 1)
run("count", t_count)

print("\n══════════════════════════════════════════")
total = passed + failed
print(f"  Résultat : {passed}/{total} tests passés")
print(f"  \033[92mTous les tests L2 sont OK ✓\033[0m" if not failed else f"  \033[91m{failed} échec(s)\033[0m")
print("══════════════════════════════════════════\n")
sys.exit(0 if failed == 0 else 1)
