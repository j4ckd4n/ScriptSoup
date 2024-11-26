import pandas as pd
import psutil
import sqlite3
import sys
import logging
import time
import os
from alive_progress import alive_bar
from multiprocessing import Pool, cpu_count

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] %(message)s')

CPU_THRESHOLD = 80 # in percentage
RAM_THRESHOLD = 80 # in percentage
ADJUST_FACTOR = 2  # Factor to reduce chunk size when resources are constrained
TEMP_DIR = os.path.join(os.environ.get("TEMP", "/temp"), "temp_parquet")
os.makedirs(TEMP_DIR, exist_ok=True)

def monitor_resources():
  cpu_percent = psutil.cpu_percent(interval=0.5)
  ram_percent = psutil.virtual_memory().percent
  logging.debug(f"CPU: {cpu_percent}%, RAM: {ram_percent}%")
  return cpu_percent < CPU_THRESHOLD and ram_percent < RAM_THRESHOLD

def get_tables(cursor):
  cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
  tables = cursor.fetchall()
  return tables

def process_chunk(args):
  sqlite_file, table, chunk_size, offset, temp_file = args
  conn = sqlite3.connect(sqlite_file)
  query = f"SELECT * FROM {table} LIMIT {chunk_size} OFFSET {offset}"
  df = pd.read_sql_query(query, conn)
  conn.close()
  df.to_parquet(temp_file, engine="fastparquet", compression="gzip", index=False)

def parallel_sqlite_to_parquet(sqlite_file, table, output_dir, chunk_size=500_000):
  conn = sqlite3.connect(sqlite_file)
  cursor = conn.cursor()
  logging.debug(f"Fetching table '{table}' size...")
  table_size = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
  logging.debug(f"Table '{table}' has {table_size} rows.")
  conn.close()

  tasks = []
  offsets = range(0, table_size, chunk_size)
  for i, offset in enumerate(offsets):
    temp_file = os.path.join(TEMP_DIR,f"chunk_{i}.parquet")
    logging.debug(f'Creating temporary file {temp_file}...')
    tasks.append((sqlite_file, table, chunk_size, offset, temp_file))

  with alive_bar(len(tasks), title=f"Converting table '{table}'") as bar:
    with Pool(cpu_count()) as pool:
      results = []
      for args in tasks:
        while not monitor_resources():
          logging.warning("Resources are constrained. Pausing...")
          time.sleep(5)

        result = pool.apply_async(process_chunk, (args,))
        results.append(result)
        bar()
    
      logging.debug(f"Waiting for all tasks to finish...")
      for result in results:
        result.wait()

      pool.close()
      pool.join()
  
  logging.debug(f"Merging Parquet files...")
  temp_files = [os.path.join(TEMP_DIR, f) for f in os.listdir(TEMP_DIR) if f.endswith(".parquet")]
  logging.debug(f"Reading temporary files...\n{temp_files}")

  first_chunk = True
  with alive_bar(len(temp_files), title=f"Merging table '{table}'") as bar:
    for file in temp_files:
      df = pd.read_parquet(file)
      df.to_parquet(f"{output_dir}/{table}.parquet", engine="fastparquet", compression="gzip", index=False, append=not first_chunk)
      first_chunk = False
      bar()

  logging.debug(f"Cleaning up temporary files...")
  for f in temp_files:
    os.remove(f)

# def chunked_sqlite_to_parquet(cursor, conn, table, chunk_size=500_000):
#   logging.debug(f"Converting table '{table}' to Parquet with chunk size {chunk_size}...")
#   logging.debug(f"Getting table size...")
#   table_size = cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
#   logging.debug(f"Table '{table}' has {table_size} rows.")
#   offset = 0
#   first_chunk = True

#   with alive_bar(table_size, title=f"Converting table '{table}'") as bar:
#     while offset < table_size:
#       query = f"SELECT * FROM {table} LIMIT {chunk_size} OFFSET {offset}"
#       df = pd.read_sql_query(query, conn)
#       df.to_parquet(f"{output_dir}/{table}.parquet", engine="fastparquet", compression="gzip", index=False, append=not first_chunk)
#       first_chunk = False
#       offset += chunk_size
#       bar(chunk_size if offset < table_size else table_size % chunk_size)

if __name__ == "__main__":
  if len(sys.argv) < 3:
    print("Usage: python sqlite_to_parquet.py <sqlite_db> <output_dir> <-v>")
    print("  -v: verbose mode")
    print("\nExample: python sqlite_to_parquet.py mydb.sqlite3 output")
    print("\nNote: This script converts all tables from a SQLite database to Parquet files. It uses gzip compression.")
    sys.exit(1)

  if "-v" in sys.argv:
    logging.getLogger().setLevel(logging.DEBUG)
    sys.argv.remove("-v")

  sqlite_db = sys.argv[1]
  output_dir = sys.argv[2]
  
  logging.debug(f"Configurations:\n - CPU_THRESHOLD: {CPU_THRESHOLD}%\n - RAM_THRESHOLD: {RAM_THRESHOLD}%\n - ADJUST_FACTOR: {ADJUST_FACTOR}\n - TEMP_DIR: {TEMP_DIR}")

  logging.debug(f"Clearing temporary directory {TEMP_DIR}...")
  temp_files = [os.path.join(TEMP_DIR, f) for f in os.listdir(TEMP_DIR) if f.endswith(".parquet")]
  for f in temp_files:
    os.remove(f)

  logging.info("Converting SQLite database to Parquet files...")

  try:
    logging.debug('Connecting to SQLite database...')
    conn = sqlite3.connect(sqlite_db)
  except Exception as e:
    logging.error(f"Error connecting to SQLite database: {e}")
    sys.exit(1)

  cursor = conn.cursor()

  logging.debug('Getting tables from SQLite database...')
  tables = get_tables(cursor)

  cursor.close()
  conn.close()

  for table in tables:
    table = table[0]
    parallel_sqlite_to_parquet(sqlite_db, table, output_dir)
