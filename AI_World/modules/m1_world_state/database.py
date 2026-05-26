import sqlite3
import json
import os
from pathlib import Path
from datetime import datetime

# Calculate project root directory (AI_World/)
ROOT_DIR = Path(__file__).resolve().parents[2]
DB_PATH = ROOT_DIR / "data" / "world.db"


def get_connection() -> sqlite3.Connection:
    """Establish and return database connection (using WAL mode for concurrent performance)"""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row  # Access columns by name
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def create_tables() -> None:
    """Create all database tables (skip if they exist)"""
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS world_meta (
                id      INTEGER PRIMARY KEY CHECK (id = 1),  -- Always exactly one row
                tick    INTEGER NOT NULL DEFAULT 0,
                year    INTEGER NOT NULL DEFAULT 1,
                season  TEXT    NOT NULL DEFAULT 'spring'
            );

            CREATE TABLE IF NOT EXISTS locations (
                id        TEXT PRIMARY KEY,
                name      TEXT NOT NULL,
                x         INTEGER NOT NULL,
                y         INTEGER NOT NULL,
                terrain   TEXT NOT NULL,
                resources TEXT NOT NULL  -- JSON
            );

            CREATE TABLE IF NOT EXISTS agents (
                id              TEXT PRIMARY KEY,
                name            TEXT NOT NULL,
                gender          TEXT NOT NULL DEFAULT 'male',
                location_id     TEXT NOT NULL,
                personality     TEXT NOT NULL,  -- JSON
                resources       TEXT NOT NULL,  -- JSON
                skills          TEXT NOT NULL,  -- JSON
                relationships   TEXT NOT NULL,  -- JSON
                memory_ids      TEXT NOT NULL,  -- JSON array
                organization_id TEXT,
                is_alive        INTEGER NOT NULL DEFAULT 1,
                age             INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS organizations (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                type        TEXT NOT NULL,
                member_ids  TEXT NOT NULL,  -- JSON array
                leader_id   TEXT,
                resources   TEXT NOT NULL,  -- JSON
                territory   TEXT NOT NULL   -- JSON array
            );

            CREATE TABLE IF NOT EXISTS events (
                id                   TEXT PRIMARY KEY,
                tick                 INTEGER NOT NULL,
                event_type           TEXT NOT NULL,
                description          TEXT NOT NULL,
                affected_agent_ids   TEXT NOT NULL,  -- JSON array
                affected_location_ids TEXT NOT NULL, -- JSON array
                timestamp            TEXT NOT NULL
            );
        """)
        
        # 動態遷移：防禦性添加 gender 欄位
        try:
            conn.execute("ALTER TABLE agents ADD COLUMN gender TEXT NOT NULL DEFAULT 'male'")
        except sqlite3.OperationalError:
            pass  # 欄位已存在
    conn.close()


def upsert_world_meta(tick: int, year: int, season: str) -> None:
    """Insert or update world_meta (always exactly one row, id=1)"""
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO world_meta (id, tick, year, season)
            VALUES (1, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET tick=excluded.tick, year=excluded.year, season=excluded.season
        """, (tick, year, season))
    conn.close()


def get_world_meta() -> dict:
    """Read world_meta, return default values if not present"""
    conn = get_connection()
    row = conn.execute("SELECT * FROM world_meta WHERE id = 1").fetchone()
    conn.close()
    if row:
        return {"tick": row["tick"], "year": row["year"], "season": row["season"]}
    return {"tick": 0, "year": 1, "season": "spring"}


def upsert_location(location_dict: dict) -> None:
    """Insert or update a location (passed using location.model_dump())"""
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO locations (id, name, x, y, terrain, resources)
            VALUES (:id, :name, :x, :y, :terrain, :resources)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, x=excluded.x, y=excluded.y,
                terrain=excluded.terrain, resources=excluded.resources
        """, {
            **location_dict,
            "resources": json.dumps(location_dict["resources"])
        })
    conn.close()


def get_all_locations() -> list[dict]:
    """Read all locations, return a list of dicts (resources parsed into dict)"""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM locations").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["resources"] = json.loads(d["resources"])
        result.append(d)
    return result


def upsert_agent(agent_dict: dict) -> None:
    """Insert or update an Agent"""
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO agents (
                id, name, gender, location_id, personality, resources,
                skills, relationships, memory_ids, organization_id, is_alive, age
            ) VALUES (
                :id, :name, :gender, :location_id, :personality, :resources,
                :skills, :relationships, :memory_ids, :organization_id, :is_alive, :age
            ) ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, gender=excluded.gender, location_id=excluded.location_id,
                personality=excluded.personality, resources=excluded.resources,
                skills=excluded.skills, relationships=excluded.relationships,
                memory_ids=excluded.memory_ids, organization_id=excluded.organization_id,
                is_alive=excluded.is_alive, age=excluded.age
        """, {
            **agent_dict,
            "personality": json.dumps(agent_dict["personality"]),
            "resources": json.dumps(agent_dict["resources"]),
            "skills": json.dumps(agent_dict["skills"]),
            "relationships": json.dumps(agent_dict["relationships"]),
            "memory_ids": json.dumps(agent_dict["memory_ids"]),
            "is_alive": 1 if agent_dict["is_alive"] else 0
        })
    conn.close()


def get_all_agents() -> list[dict]:
    """Read all Agents, return a list of dicts (nested fields parsed)"""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM agents").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["personality"] = json.loads(d["personality"])
        d["resources"] = json.loads(d["resources"])
        d["skills"] = json.loads(d["skills"])
        d["relationships"] = json.loads(d["relationships"])
        d["memory_ids"] = json.loads(d["memory_ids"])
        d["is_alive"] = bool(d["is_alive"])
        result.append(d)
    return result


def upsert_organization(org_dict: dict) -> None:
    """Insert or update an organization"""
    conn = get_connection()
    with conn:
        conn.execute("""
            INSERT INTO organizations (id, name, type, member_ids, leader_id, resources, territory)
            VALUES (:id, :name, :type, :member_ids, :leader_id, :resources, :territory)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name, type=excluded.type, member_ids=excluded.member_ids,
                leader_id=excluded.leader_id, resources=excluded.resources, territory=excluded.territory
        """, {
            **org_dict,
            "member_ids": json.dumps(org_dict["member_ids"]),
            "resources": json.dumps(org_dict["resources"]),
            "territory": json.dumps(org_dict["territory"])
        })
    conn.close()


def get_all_organizations() -> list[dict]:
    """Read all organizations, return a list of dicts"""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM organizations").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["member_ids"] = json.loads(d["member_ids"])
        d["resources"] = json.loads(d["resources"])
        d["territory"] = json.loads(d["territory"])
        result.append(d)
    return result


def insert_event(event_dict: dict) -> None:
    """Insert a new event (insert-only, no update)"""
    conn = get_connection()
    ts = event_dict["timestamp"]
    if isinstance(ts, datetime):
        ts_str = ts.isoformat()
    else:
        ts_str = str(ts)
        
    with conn:
        conn.execute("""
            INSERT INTO events (id, tick, event_type, description, affected_agent_ids, affected_location_ids, timestamp)
            VALUES (:id, :tick, :event_type, :description, :affected_agent_ids, :affected_location_ids, :timestamp)
        """, {
            **event_dict,
            "affected_agent_ids": json.dumps(event_dict["affected_agent_ids"]),
            "affected_location_ids": json.dumps(event_dict["affected_location_ids"]),
            "timestamp": ts_str
        })
    conn.close()


def get_all_events() -> list[dict]:
    """Read all events, return a list of dicts"""
    conn = get_connection()
    rows = conn.execute("SELECT * FROM events").fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        d["affected_agent_ids"] = json.loads(d["affected_agent_ids"])
        d["affected_location_ids"] = json.loads(d["affected_location_ids"])
        try:
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        except ValueError:
            # Fallback to current time if parsing fails
            d["timestamp"] = datetime.now()
        result.append(d)
    return result
