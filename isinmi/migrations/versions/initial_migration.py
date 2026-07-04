# Copyright 2026 Sébastien Demanou. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Initial encrypted SQLite schema.

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-03
"""
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS alerts (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            severity TEXT NOT NULL CHECK (severity IN ('info','warning','critical')),
            timestamp TEXT NOT NULL,
            source TEXT,
            tags TEXT NOT NULL DEFAULT '[]',
            acknowledged INTEGER NOT NULL DEFAULT 0,
            acknowledged_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            datetime TEXT NOT NULL,
            recurring TEXT NOT NULL CHECK (recurring IN ('none','daily','weekly','monthly')),
            tags TEXT NOT NULL DEFAULT '[]',
            status TEXT NOT NULL CHECK (status IN ('pending','completed','dismissed')),
            created_at TEXT NOT NULL,
            notified_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            start_datetime TEXT NOT NULL,
            end_datetime TEXT NOT NULL,
            location TEXT,
            attendees TEXT NOT NULL DEFAULT '[]',
            tags TEXT NOT NULL DEFAULT '[]',
            reminders TEXT NOT NULL DEFAULT '[15,30,60]',
            status TEXT NOT NULL CHECK (status IN ('scheduled','ongoing','completed','cancelled')),
            created_at TEXT NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notifications (
            id TEXT PRIMARY KEY,
            type TEXT NOT NULL CHECK (type IN ('alert','reminder','event')),
            message TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]',
            timestamp TEXT NOT NULL,
            read_status INTEGER NOT NULL DEFAULT 0,
            read_at TEXT
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_conversations (
            id TEXT PRIMARY KEY,
            message TEXT NOT NULL,
            response TEXT NOT NULL,
            action_type TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            tags TEXT NOT NULL DEFAULT '[]',
            context TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
    )
    for statement in [
        "CREATE INDEX IF NOT EXISTS idx_alerts_timestamp ON alerts(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_severity ON alerts(severity)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_acknowledged ON alerts(acknowledged)",
        "CREATE INDEX IF NOT EXISTS idx_alerts_tags ON alerts(tags)",
        "CREATE INDEX IF NOT EXISTS idx_reminders_datetime ON reminders(datetime)",
        "CREATE INDEX IF NOT EXISTS idx_reminders_status ON reminders(status)",
        "CREATE INDEX IF NOT EXISTS idx_reminders_tags ON reminders(tags)",
        "CREATE INDEX IF NOT EXISTS idx_events_start_datetime ON events(start_datetime)",
        "CREATE INDEX IF NOT EXISTS idx_events_end_datetime ON events(end_datetime)",
        "CREATE INDEX IF NOT EXISTS idx_events_status ON events(status)",
        "CREATE INDEX IF NOT EXISTS idx_events_tags ON events(tags)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_timestamp ON notifications(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_type ON notifications(type)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_entity_id ON notifications(entity_id)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_read_status ON notifications(read_status)",
        "CREATE INDEX IF NOT EXISTS idx_notifications_tags ON notifications(tags)",
    ]:
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS agent_conversations")
    op.execute("DROP TABLE IF EXISTS notifications")
    op.execute("DROP TABLE IF EXISTS events")
    op.execute("DROP TABLE IF EXISTS reminders")
    op.execute("DROP TABLE IF EXISTS alerts")
