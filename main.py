
import sqlite3
from contextlib import contextmanager
from fastapi import FastAPI, HTTPException
import uvicorn
app = FastAPI(title="Enterprise Agent Entitlements")

DB = "entitlements.db"

@contextmanager
def db_connection():
    conn = sqlite3.connect(DB)
    try:
        yield conn
    finally:
        conn.close()

def initialize_database():
    with db_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS agents (
                tenant_id TEXT NOT NULL,
                agent_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                PRIMARY KEY (tenant_id, agent_id)
            );

            CREATE TABLE IF NOT EXISTS entitlements (
                tenant_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                agent_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                PRIMARY KEY (
                    tenant_id, user_id, agent_id, action
                ),
                FOREIGN KEY (tenant_id, agent_id)
                    REFERENCES agents (tenant_id, agent_id)
            );
        """)

        conn.executemany(
            "INSERT OR IGNORE INTO agents VALUES (?, ?, ?)",
            [
                ("tenant-a", 1, "Finance Agent"),
                ("tenant-a", 2, "HR Agent"),
                ("tenant-a", 3, "Payroll Agent"),
                ("tenant-a", 4, "Support Agent")
            ]
        )

        conn.executemany(
            "INSERT OR IGNORE INTO entitlements VALUES (?, ?, ?, ?)",
            [
                ("tenant-a", "chetana", 1, "invoke"),
                ("tenant-a", "chetana", 2, "invoke"),
                ("tenant-a", "chetana", 4, "invoke"),
                ("tenant-a", "rahul", 1, "invoke"),
                ("tenant-a", "rahul", 3, "invoke")
            ]
        )
        conn.commit()

initialize_database()


def can_invoke(tenant_id: str, user_id: str, agent_id: int):
    with db_connection() as conn:
        result = conn.execute(
            """
            SELECT 1
            FROM entitlements
            WHERE tenant_id = ?
              AND user_id = ?
              AND agent_id = ?
              AND action = 'invoke'
            """,
            (tenant_id, user_id, agent_id)
        ).fetchone()

        return result is not None



def get_demo_identity():
    # represents a previously authenticated user.
    return {
        "tenant_id": "tenant-a",
        "user_id": "chetana"
    }

@app.post("/agents/{agent_id}/invoke")
def invoke_agent(agent_id: int):
    identity = get_demo_identity()

    tenant_id = identity["tenant_id"]
    user_id = identity["user_id"]

    # First verify that this agent belongs to this tenant.
    with db_connection() as conn:
        agent = conn.execute(
            """
            SELECT name FROM agents
            WHERE tenant_id = ? AND agent_id = ?
            """,
            (tenant_id, agent_id)
        ).fetchone()

    if agent is None:
        raise HTTPException(
            status_code=404,
            detail="Agent not found"
        )

    if not can_invoke(tenant_id, user_id, agent_id):
        raise HTTPException(
            status_code=403,
            detail="Access denied: no invoke entitlement"
        )

    # Replace this with a real orchestrator invocation later.
    return {
        "status": "accepted",
        "agent": agent[0],
        "user": user_id,
        "message": "Authorized - agent invocation would start here"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)