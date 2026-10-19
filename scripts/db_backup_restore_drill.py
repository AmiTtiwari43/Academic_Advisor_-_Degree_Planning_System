"""
Automated Database Backup and Restore Drill for Phase 10 Release.
Dumps degree_planning_dev to SQL, restores into degree_planning_scratch,
and compares row counts across all application tables.
"""

import subprocess
import sys

import psycopg

CONTAINER_NAME = "degree_planning_postgres"
SRC_DB = "degree_planning_dev"
SCRATCH_DB = "degree_planning_scratch"
DB_USER = "postgres"
DB_PASSWORD = "postgres_dev_password"


def run_cmd(cmd_list: list[str]) -> subprocess.CompletedProcess:
    res = subprocess.run(cmd_list, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error executing {cmd_list}: {res.stderr}")
        sys.exit(1)
    return res


def main():
    print(f"=== Starting DB Backup and Restore Drill for {SRC_DB} ===")

    # 1. Create a clean backup using pg_dump
    print("1. Creating pg_dump snapshot...")
    dump_cmd = [
        "docker",
        "exec",
        "-i",
        CONTAINER_NAME,
        "pg_dump",
        "-U",
        DB_USER,
        "-d",
        SRC_DB,
    ]
    res_dump = run_cmd(dump_cmd)
    sql_dump = res_dump.stdout
    print(f"   Dump generated successfully ({len(sql_dump)} characters).")

    # 2. Prepare scratch database
    print(f"2. Preparing scratch database: {SCRATCH_DB}...")
    drop_scratch_cmd = [
        "docker",
        "exec",
        "-i",
        CONTAINER_NAME,
        "psql",
        "-U",
        DB_USER,
        "-c",
        f"DROP DATABASE IF EXISTS {SCRATCH_DB};",
    ]
    run_cmd(drop_scratch_cmd)

    create_scratch_cmd = [
        "docker",
        "exec",
        "-i",
        CONTAINER_NAME,
        "psql",
        "-U",
        DB_USER,
        "-c",
        f"CREATE DATABASE {SCRATCH_DB};",
    ]
    run_cmd(create_scratch_cmd)
    print(f"   Scratch database {SCRATCH_DB} created.")

    # 3. Restore dump into scratch database
    print("3. Restoring snapshot into scratch database...")
    restore_proc = subprocess.Popen(
        [
            "docker",
            "exec",
            "-i",
            CONTAINER_NAME,
            "psql",
            "-U",
            DB_USER,
            "-d",
            SCRATCH_DB,
            "-q",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = restore_proc.communicate(input=sql_dump)
    if restore_proc.returncode != 0:
        print(f"Error during restore: {stderr}")
        sys.exit(1)
    print("   Restore completed.")

    # 4. Compare row counts across all tables
    print("4. Comparing table row counts between source and restored database...")
    src_conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@localhost:5432/{SRC_DB}"
    scratch_conn_str = f"postgresql://{DB_USER}:{DB_PASSWORD}@localhost:5432/{SCRATCH_DB}"

    with psycopg.connect(src_conn_str) as src_conn, psycopg.connect(scratch_conn_str) as scratch_conn:
        with src_conn.cursor() as src_cur, scratch_conn.cursor() as scratch_cur:
            src_cur.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name;
                """
            )
            tables = [row[0] for row in src_cur.fetchall()]

            print(f"\n{'Table Name':<35} | {'Source Rows':<12} | {'Restored Rows':<14} | {'Status'}")
            print("-" * 75)

            all_matched = True
            for tbl in tables:
                src_cur.execute(f'SELECT COUNT(*) FROM "{tbl}";')
                src_count = src_cur.fetchone()[0]

                scratch_cur.execute(f'SELECT COUNT(*) FROM "{tbl}";')
                scratch_count = scratch_cur.fetchone()[0]

                is_match = (src_count == scratch_count)
                status_str = "MATCH" if is_match else "MISMATCH"
                if not is_match:
                    all_matched = False

                print(f"{tbl:<35} | {src_count:<12} | {scratch_count:<14} | {status_str}")

            print("-" * 75)
            if all_matched:
                print(f"SUCCESS: All {len(tables)} tables matched row-for-row between {SRC_DB} and {SCRATCH_DB}.")
            else:
                print("FAILURE: One or more tables had mismatched row counts.")
                sys.exit(1)


if __name__ == "__main__":
    main()
