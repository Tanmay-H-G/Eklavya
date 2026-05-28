"""
db_viewer.py — Eklavya Database Inspector
==========================================
Run from the eklavya/ folder:
    python db_viewer.py

Shows all tables, users, conversation history, preferences, and sessions
in a clean, readable format directly in the terminal.
No extra dependencies required — uses only Python's built-in sqlite3.
"""

import sqlite3
import os
import sys
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eklavya.db')

# ── ANSI colours ──────────────────────────────────────────────────────────────
class C:
    BOLD   = '\033[1m'
    CYAN   = '\033[96m'
    GREEN  = '\033[92m'
    YELLOW = '\033[93m'
    RED    = '\033[91m'
    BLUE   = '\033[94m'
    GREY   = '\033[90m'
    RESET  = '\033[0m'

def h(text, color=C.CYAN):
    return f"{color}{C.BOLD}{text}{C.RESET}"

def banner(title):
    w = 60
    print()
    print(h('═' * w, C.BLUE))
    print(h(f"  {title}", C.BLUE))
    print(h('═' * w, C.BLUE))

def section(title):
    print()
    print(h(f"── {title} {'─' * (50 - len(title))}", C.CYAN))

def fmt_ts(ts):
    if not ts:
        return C.GREY + 'never' + C.RESET
    return C.GREY + str(ts)[:16] + C.RESET


# ── DB Connection ─────────────────────────────────────────────────────────────

def get_conn():
    if not os.path.exists(DB_PATH):
        print(f"{C.RED}✗ Database not found: {DB_PATH}{C.RESET}")
        print(f"  Run 'python main.py' first to create it.")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


# ── Summary ───────────────────────────────────────────────────────────────────

def show_summary(conn):
    banner("EKLAVYA DATABASE SUMMARY")
    cu = conn.cursor()

    db_size = os.path.getsize(DB_PATH)
    print(f"\n  📁 File      : {DB_PATH}")
    print(f"  💾 Size      : {db_size / 1024:.1f} KB")
    print(f"  🕐 Viewed at : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Table row counts
    tables = ['users', 'conversations', 'preferences', 'sessions']
    print()
    print(f"  {'TABLE':<20} {'ROWS':>8}")
    print(f"  {'─'*20} {'─'*8}")
    for t in tables:
        try:
            cu.execute(f'SELECT COUNT(*) FROM {t}')
            count = cu.fetchone()[0]
            print(f"  {t:<20} {count:>8,}")
        except Exception:
            print(f"  {t:<20} {'(missing)':>8}")


# ── Users ─────────────────────────────────────────────────────────────────────

def show_users(conn):
    section("USERS")
    cu = conn.cursor()
    cu.execute('SELECT id, username, email, phone, hash_algo, created_at, last_login FROM users ORDER BY id')
    rows = cu.fetchall()
    if not rows:
        print(f"  {C.GREY}No users registered yet.{C.RESET}")
        return

    print(f"\n  {'ID':<4} {'USERNAME':<18} {'EMAIL':<26} {'PHONE':<16} {'ALGO':<8} {'CREATED':<17} {'LAST LOGIN'}")
    print(f"  {'─'*4} {'─'*18} {'─'*26} {'─'*16} {'─'*8} {'─'*17} {'─'*17}")
    for r in rows:
        uid, uname, email, phone, algo, created, last_login = r
        print(f"  {C.GREEN}{uid:<4}{C.RESET} "
              f"{C.BOLD}{uname:<18}{C.RESET} "
              f"{(email or '–'):<26} "
              f"{(phone or '–'):<16} "
              f"{C.YELLOW}{(algo or '?'):<8}{C.RESET} "
              f"{fmt_ts(created):<17} "
              f"{fmt_ts(last_login)}")
    print(f"\n  Total: {h(str(len(rows)), C.GREEN)} user(s)")


# ── Conversations ─────────────────────────────────────────────────────────────

def show_conversations(conn, limit=20, user_id=None):
    title = f"RECENT CONVERSATIONS (last {limit})" + (f" — user_id={user_id}" if user_id else " — all users")
    section(title)
    cu = conn.cursor()

    if user_id:
        cu.execute(
            '''SELECT c.id, u.username, c.session_id, c.role, c.content, c.timestamp
               FROM conversations c JOIN users u ON u.id = c.user_id
               WHERE c.user_id=?
               ORDER BY c.timestamp DESC LIMIT ?''',
            (user_id, limit)
        )
    else:
        cu.execute(
            '''SELECT c.id, u.username, c.session_id, c.role, c.content, c.timestamp
               FROM conversations c JOIN users u ON u.id = c.user_id
               ORDER BY c.timestamp DESC LIMIT ?''',
            (limit,)
        )

    rows = cu.fetchall()
    if not rows:
        print(f"  {C.GREY}No conversations yet.{C.RESET}")
        return

    for r in reversed(rows):
        cid, uname, session, role, content, ts = r
        role_color = C.BLUE if role == 'user' else C.GREEN if role == 'assistant' else C.YELLOW
        truncated  = content[:90] + ('…' if len(content) > 90 else '')
        print(f"  {C.GREY}[{cid}] {fmt_ts(ts)}{C.RESET} "
              f"{C.BOLD}{uname}{C.RESET} "
              f"{role_color}[{role}]{C.RESET}: {truncated}")
    print(f"\n  Showing {len(rows)} of total messages stored.")


# ── Preferences ───────────────────────────────────────────────────────────────

def show_preferences(conn):
    section("USER PREFERENCES")
    cu = conn.cursor()
    cu.execute(
        '''SELECT u.username, p.key, p.value FROM preferences p
           JOIN users u ON u.id = p.user_id ORDER BY u.username, p.key'''
    )
    rows = cu.fetchall()
    if not rows:
        print(f"  {C.GREY}No preferences set yet.{C.RESET}")
        return

    print(f"\n  {'USER':<20} {'KEY':<20} VALUE")
    print(f"  {'─'*20} {'─'*20} {'─'*20}")
    for username, key, value in rows:
        print(f"  {C.BOLD}{username:<20}{C.RESET} {C.YELLOW}{key:<20}{C.RESET} {value}")


# ── Sessions ──────────────────────────────────────────────────────────────────

def show_sessions(conn):
    section("ACTIVE SESSIONS (Remember-Me Tokens)")
    cu = conn.cursor()
    cu.execute(
        '''SELECT u.username, s.token, s.created_at, s.expires_at
           FROM sessions s JOIN users u ON u.id = s.user_id
           WHERE s.expires_at > CURRENT_TIMESTAMP ORDER BY s.created_at DESC'''
    )
    rows = cu.fetchall()
    if not rows:
        print(f"  {C.GREY}No active sessions.{C.RESET}")
        return

    print(f"\n  {'USER':<20} {'TOKEN (first 20 chars)':<24} {'CREATED':<17} EXPIRES")
    print(f"  {'─'*20} {'─'*24} {'─'*17} {'─'*17}")
    for username, token, created, expires in rows:
        print(f"  {C.BOLD}{username:<20}{C.RESET} "
              f"{C.GREY}{token[:20]}…{C.RESET}  "
              f"{fmt_ts(created)}  {fmt_ts(expires)}")
    print(f"\n  {C.GREEN}✓{C.RESET} {len(rows)} active session(s)")


# ── Interactive Menu ──────────────────────────────────────────────────────────

def main():
    try:
        conn = get_conn()
    except SystemExit:
        return

    while True:
        banner("EKLAVYA DATABASE VIEWER")
        print(f"\n  {h('1', C.GREEN)} Summary & table sizes")
        print(f"  {h('2', C.GREEN)} Show all users")
        print(f"  {h('3', C.GREEN)} Show recent conversations (all users)")
        print(f"  {h('4', C.GREEN)} Show conversations for a specific user")
        print(f"  {h('5', C.GREEN)} Show preferences")
        print(f"  {h('6', C.GREEN)} Show active sessions")
        print(f"  {h('7', C.GREEN)} Run custom SQL query")
        print(f"  {h('0', C.RED)}  Exit")
        print()

        choice = input("  Choose an option: ").strip()

        if choice == '1':
            show_summary(conn)
        elif choice == '2':
            show_users(conn)
        elif choice == '3':
            n = input("  How many messages to show? [20]: ").strip()
            show_conversations(conn, limit=int(n) if n.isdigit() else 20)
        elif choice == '4':
            show_users(conn)
            uid = input("  Enter user ID: ").strip()
            n   = input("  How many messages? [20]: ").strip()
            if uid.isdigit():
                show_conversations(conn, limit=int(n) if n.isdigit() else 20, user_id=int(uid))
        elif choice == '5':
            show_preferences(conn)
        elif choice == '6':
            show_sessions(conn)
        elif choice == '7':
            print(f"\n  {C.YELLOW}Enter SQL (e.g. SELECT * FROM users LIMIT 5):{C.RESET}")
            sql = input("  SQL> ").strip()
            if sql:
                try:
                    cu = conn.cursor()
                    cu.execute(sql)
                    rows = cu.fetchall()
                    if rows:
                        cols = [d[0] for d in cu.description]
                        print(f"\n  {' | '.join(cols)}")
                        print(f"  {'─' * 60}")
                        for r in rows:
                            print(f"  {' | '.join(str(x) for x in r)}")
                        print(f"\n  {len(rows)} row(s) returned.")
                    else:
                        print(f"  {C.GREY}No rows returned.{C.RESET}")
                except Exception as e:
                    print(f"  {C.RED}SQL Error: {e}{C.RESET}")
        elif choice == '0':
            print(f"\n  {C.GREEN}Bye!{C.RESET}\n")
            break
        else:
            print(f"  {C.RED}Invalid choice. Try again.{C.RESET}")

        input(f"\n  {C.GREY}Press Enter to continue…{C.RESET}")

    conn.close()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n  {C.GREEN}Exited.{C.RESET}\n")
