"""
Test L4 — PostgreSQL (faits validés, recherche, compactage)
Vérifie : connexion, tables, commit, search, usage_count, compactage.

Prérequis : docker compose up -d
Lancer    : python test_data/test_memory_l4.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("OPENAI_API_KEY", "fake")

from Memory.team_agent.memory import l4_save, l4_search, l4_compact, _pg_conn

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

def count_facts(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM memory_facts WHERE is_active=TRUE")
        return cur.fetchone()[0]

def count_total(conn) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM memory_facts")
        return cur.fetchone()[0]

print("\n══════════════════════════════════════════")
print("  TEST L4 — PostgreSQL")
print("══════════════════════════════════════════\n")

print("▶ Connexion PostgreSQL")
def t_connexion():
    conn = _pg_conn()
    assert conn is not None, "PostgreSQL non disponible — docker compose up -d ?"
    assert not conn.closed, "Connexion fermée"
    check("connexion active", True)

    # Tables existantes
    with conn.cursor() as cur:
        cur.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = [r[0] for r in cur.fetchall()]
    print(f"       Tables : {tables}")
    check("table memory_facts présente", "memory_facts" in tables)

    active = count_facts(conn)
    total  = count_total(conn)
    print(f"       Faits actifs : {active} / {total} total")
    conn.close()
run("connexion + tables", t_connexion)

print("\n▶ Colonnes de memory_facts")
def t_schema():
    conn = _pg_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'memory_facts'
            ORDER BY ordinal_position
        """)
        cols = cur.fetchall()
    conn.close()
    print(f"       Colonnes ({len(cols)}) :")
    for name, dtype, nullable in cols:
        print(f"         {name:<20} {dtype:<20} {'NULL' if nullable == 'YES' else 'NOT NULL'}")
    col_names = [c[0] for c in cols]
    for expected in ["id", "content", "category", "confidence", "is_active", "usage_count", "created_at"]:
        check(f"colonne '{expected}' présente", expected in col_names)
run("schema", t_schema)

print("\n▶ Commit de faits")
def t_commit():
    faits = [
        ("Je préfère toujours utiliser Python pour les projets IA", "preference", 0.95),
        ("Objectif : réduire les tokens par session au minimum", "goal", 0.9),
        ("Règle : chaque agent valide son output avant de transmettre", "rule", 1.0),
        ("Le projet utilise LangGraph comme orchestrateur principal", "fact", 0.85),
    ]
    conn = _pg_conn()
    avant = count_facts(conn)
    conn.close()
    for content, cat, conf in faits:
        ok = l4_save(content, category=cat, confidence=conf)
        check(f"commit [{cat}] conf={conf}", ok is True, content[:45])
    conn = _pg_conn()
    apres = count_facts(conn)
    conn.close()
    print(f"       Faits actifs : {avant} → {apres} (+{apres - avant})")
run("commit", t_commit)

print("\n▶ Recherche full-text")
def t_search():
    results = l4_search("python", k=5)
    check(f"{len(results)} résultat(s)", len(results) > 0)
    if results:
        print(f"       Meilleur résultat : \"{results[0].page_content[:60]}\"")
        check("layer=L4", results[0].metadata.get("layer") == "L4")
        check("contient 'python'", "python" in results[0].page_content.lower())

    results2 = l4_search("token session réduction", k=3)
    check(f"{len(results2)} résultat(s) pour 'token'", len(results2) >= 0)
run("search", t_search)

print("\n▶ Statistiques par catégorie")
def t_stats():
    conn = _pg_conn()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT category, COUNT(*), AVG(confidence)::numeric(4,2), SUM(usage_count)
            FROM memory_facts WHERE is_active=TRUE
            GROUP BY category ORDER BY COUNT(*) DESC
        """)
        rows = cur.fetchall()
    conn.close()
    print(f"       {'Catégorie':<20} {'Nb':<6} {'Conf moy':<10} {'Usages'}")
    print(f"       {'-'*50}")
    for cat, nb, conf, usages in rows:
        print(f"       {cat:<20} {nb:<6} {float(conf):<10.2f} {usages}")
    check("au moins 1 catégorie", len(rows) > 0)
run("stats", t_stats)

print("\n▶ Compactage")
def t_compact():
    msg = l4_compact()
    print(f"       {msg}")
    check("l4_compact retourne un résumé", isinstance(msg, str) and len(msg) > 0)
run("compactage", t_compact)

print("\n══════════════════════════════════════════")
total = passed + failed
print(f"  Résultat : {passed}/{total} tests passés")
print(f"  \033[92mTous les tests L4 sont OK ✓\033[0m" if not failed else f"  \033[91m{failed} échec(s)\033[0m")
print("══════════════════════════════════════════\n")
sys.exit(0 if failed == 0 else 1)
