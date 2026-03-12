from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

# Add an entry here for each table that needs RLS
_RLS_POLICIES = [
    {
        "table": "timeseries",
        "policy": "timeseries_owner_policy",
        "using": "owner_id = current_setting('app.current_user_id')::int",
        "check": "owner_id = current_setting('app.current_user_id')::int",
    },
]


async def setup_database(conn: AsyncConnection) -> None:
    for cfg in _RLS_POLICIES:
        table = cfg["table"]
        policy = cfg["policy"]
        await conn.execute(text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        await conn.execute(text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        await conn.execute(text(f"""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_policies
                    WHERE tablename = '{table}' AND policyname = '{policy}'
                ) THEN
                    CREATE POLICY {policy} ON {table}
                        USING ({cfg["using"]})
                        WITH CHECK ({cfg["check"]});
                END IF;
            END $$;
        """))
