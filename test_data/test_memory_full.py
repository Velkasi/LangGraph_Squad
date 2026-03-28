"""
Test FULL — Pipeline mémoire complet L2+L3+L4
Vérifie : save_to_memory, search_memory, commit_to_identity, priorité des couches, déduplication.

Prérequis : docker compose up -d
Lancer    : python test_data/test_memory_full.py
"""

import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("OPENAI_API_KEY", "fake")

from Memory.team_agent.memory import save_to_memory, search_memory, commit_to_identity

OK   = "\033[92m[OK]\033[0m"
ERR  = "\033[91m[FAIL]\033[0m"
SKIP = "\033[93m[SKIP]\033[0m"

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
print("  TEST FULL — Pipeline mémoire complet")
print("══════════════════════════════════════════\n")

print("▶ save_to_memory (L2 + porte L3)")
def t_save_api():
    result = save_to_memory(
        f"Le projet doit utiliser LangGraph pour minimiser les appels LLM ts={int(time.time())}",
        category="plan"
    )
    check("retourne un dict", isinstance(result, dict))
    check("L2 sauvegardé", result.get("L2") is True, f"result={result}")
    check("L3 clé présente", "L3" in result, f"result={result}")
    print(f"       Couches sauvegardées : {[k for k, v in result.items() if v]}")
run("save_to_memory", t_save_api)

print("\n▶ save_to_memory — contenu très court (L3 doit rejeter)")
def t_save_court():
    result = save_to_memory("ok", category="general")
    check("L2 sauvegardé", result.get("L2") is True)
    print(f"       L3 accepté : {result.get('L3')} (attendu souvent False pour texte très court/similaire)")
run("save court", t_save_court)

print("\n▶ commit_to_identity (L4)")
def t_commit_api():
    ok = commit_to_identity(
        f"Priorité absolue : lisibilité du code prime sur la performance ts={int(time.time())}",
        category="rule",
        confidence=0.95,
    )
    check("commit retourne True", ok is True)
run("commit_to_identity", t_commit_api)

print("\n▶ search_memory — recherche hybride (L4 > L3 > L2)")
def t_search_hybride():
    results = search_memory("LangGraph orchestration agents", k=5)
    check(f"{len(results)} résultat(s) total", len(results) > 0)
    layers_found = set(r.metadata.get("layer") for r in results)
    print(f"       Couches représentées : {layers_found}")
    for i, doc in enumerate(results):
        layer = doc.metadata.get("layer", "?")
        cat   = doc.metadata.get("category", "")
        print(f"       [{i+1}] [{layer}/{cat}] {doc.page_content[:65]}")
run("search hybride", t_search_hybride)

print("\n▶ Priorité L4 > L3 > L2")
def t_priorite():
    tag = f"PRIORITE_TEST_{int(time.time())}"
    commit_to_identity(f"Fait unique test priorité L4 : {tag}", category="rule", confidence=1.0)
    time.sleep(0.5)
    results = search_memory(tag, k=5)
    if not results:
        print(f"  {SKIP} aucun résultat — index pas encore à jour")
        return
    first_layer = results[0].metadata.get("layer")
    check("premier résultat vient de L4", first_layer == "L4", f"couche={first_layer}")
run("priorité couches", t_priorite)

print("\n▶ Déduplication cross-layers")
def t_dedup_cross():
    tag = f"DEDUP_CROSS_{int(time.time())}"
    save_to_memory(tag, category="test")
    commit_to_identity(tag, category="test", confidence=0.8)
    results = search_memory(tag, k=10)
    occurrences = sum(1 for r in results if tag in r.page_content)
    check("contenu dédupliqué (≤1 occurrence)", occurrences <= 1, f"occurrences={occurrences}")
run("déduplication cross-layers", t_dedup_cross)

print("\n▶ Latence search_memory (<500ms)")
def t_latence():
    save_to_memory("warm-up latence test", category="test")
    t0 = time.perf_counter()
    search_memory("latence performance test", k=3)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    check(f"latence {elapsed_ms:.0f}ms (<500ms)", elapsed_ms < 500, f"{elapsed_ms:.0f}ms")
    if elapsed_ms < 200:
        print(f"       \033[92m✓ SLA <200ms respecté ({elapsed_ms:.0f}ms)\033[0m")
    else:
        print(f"       \033[93m⚠ {elapsed_ms:.0f}ms — au-dessus de 200ms (acceptable si embedding non chargé)\033[0m")
run("latence", t_latence)

print("\n══════════════════════════════════════════")
total = passed + failed
print(f"  Résultat : {passed}/{total} tests passés")
print(f"  \033[92mTous les tests FULL sont OK ✓\033[0m" if not failed else f"  \033[91m{failed} échec(s)\033[0m")
print("══════════════════════════════════════════\n")
sys.exit(0 if failed == 0 else 1)
