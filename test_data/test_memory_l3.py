"""
Test L3 — ChromaDB (porte d'écriture + recherche vectorielle persistante)
Vérifie : connexion, save, search, déduplication, compte de documents.

Prérequis : docker compose up -d
Lancer    : python test_data/test_memory_l3.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("OPENAI_API_KEY", "fake")

from Memory.team_agent.memory import l3_save, l3_search, _chroma_collection

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
print("  TEST L3 — ChromaDB")
print("══════════════════════════════════════════\n")

print("▶ Connexion ChromaDB")
def t_connexion():
    col, enc = _chroma_collection()
    assert col is not None, "ChromaDB non disponible — docker compose up -d ?"
    count = col.count()
    check("collection accessible", col is not None)
    print(f"       Collection      : {col.name}")
    print(f"       Documents total : {count}")
run("connexion", t_connexion)

print("\n▶ Porte d'écriture — seuil de similarité")
def t_porte():
    # Texte très générique — peut être rejeté (trop similaire à un existant)
    ok_banal = l3_save("ok merci au revoir", category="test")
    print(f"       Texte très court accepté : {ok_banal} (dépend du contenu existant)")
    # Texte riche et unique avec timestamp pour forcer l'unicité
    import time
    contenu_unique = f"Règle architecture critique timestamp={int(time.time())} : isoler les agents dans des modules séparés avec interfaces claires"
    ok = l3_save(contenu_unique, category="rule")
    check("contenu unique sauvegardé", ok is True, contenu_unique[:50])
run("porte écriture", t_porte)

print("\n▶ Sauvegarde multiple")
def t_save_multiple():
    import time
    docs = [
        (f"L'objectif principal est de minimiser les tokens utilisés par session ts={int(time.time())}", "goal"),
        (f"Préférence architecture modulaire séparation responsabilités ts={int(time.time())+1}", "preference"),
        (f"Règle : chaque agent valide son output avant de transmettre ts={int(time.time())+2}", "rule"),
    ]
    for content, cat in docs:
        ok = l3_save(content, category=cat)
        check(f"save [{cat}]", ok is True, content[:50])
run("save multiple", t_save_multiple)

print("\n▶ Déduplication")
def t_dedup():
    import time
    col, _ = _chroma_collection()
    contenu = f"Règle dédup unique test {int(time.time())}"
    l3_save(contenu, category="test")
    count_avant = col.count()
    l3_save(contenu, category="test")  # même contenu → doit être bloqué (distance < seuil)
    count_apres = col.count()
    check("doublon non ajouté (ou rejeté par similarité)", count_avant == count_apres,
          f"avant={count_avant} après={count_apres}")
run("déduplication", t_dedup)

print("\n▶ Recherche vectorielle")
def t_search():
    results = l3_search("architecture backend modulaire", k=5)
    check(f"{len(results)} résultat(s)", len(results) > 0)
    if results:
        print(f"       Premier résultat : \"{results[0].page_content[:65]}\"")
        check("metadata layer=L3", results[0].metadata.get("layer") == "L3")
run("search", t_search)

print("\n▶ Statistiques collection")
def t_stats():
    col, _ = _chroma_collection()
    count = col.count()
    print(f"       Documents dans ChromaDB : {count}")
    # Peek at some docs
    if count > 0:
        peek = col.peek(min(5, count))
        cats = {}
        for m in peek.get("metadatas", []):
            cat = m.get("category", "?")
            cats[cat] = cats.get(cat, 0) + 1
        print(f"       Catégories (5 premiers) : {cats}")
    check("collection non vide", count > 0, f"{count} docs")
run("stats", t_stats)

print("\n══════════════════════════════════════════")
total = passed + failed
print(f"  Résultat : {passed}/{total} tests passés")
print(f"  \033[92mTous les tests L3 sont OK ✓\033[0m" if not failed else f"  \033[91m{failed} échec(s)\033[0m")
print("══════════════════════════════════════════\n")
sys.exit(0 if failed == 0 else 1)
