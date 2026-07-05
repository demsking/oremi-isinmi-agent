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
"""Initial ORM schema."""
import sqlalchemy as sa
from alembic import op


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
  op.create_table(
    "alerts",
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("title", sa.String(length=200), nullable=False),
    sa.Column("message", sa.String(), nullable=False),
    sa.Column("severity", sa.String(length=16), nullable=False),
    sa.Column("timestamp", sa.DateTime(), nullable=False),
    sa.Column("source", sa.String(length=100), nullable=True),
    sa.Column("tags", sa.JSON(), nullable=False),
    sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
    sa.CheckConstraint("severity IN ('info', 'warning', 'critical')", name="ck_alerts_severity"),
  )
  op.create_table(
    "reminders",
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("title", sa.String(length=200), nullable=False),
    sa.Column("description", sa.String(length=500), nullable=True),
    sa.Column("datetime", sa.DateTime(), nullable=False),
    sa.Column("recurring", sa.String(length=16), nullable=False),
    sa.Column("tags", sa.JSON(), nullable=False),
    sa.Column("status", sa.String(length=16), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False),
    sa.Column("notified_at", sa.DateTime(), nullable=True),
    sa.CheckConstraint("recurring IN ('none', 'daily', 'weekly', 'monthly')", name="ck_reminders_recurring"),
    sa.CheckConstraint("status IN ('pending', 'completed', 'dismissed')", name="ck_reminders_status"),
  )
  op.create_table(
    "events",
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("title", sa.String(length=200), nullable=False),
    sa.Column("description", sa.String(length=500), nullable=True),
    sa.Column("start_datetime", sa.DateTime(), nullable=False),
    sa.Column("end_datetime", sa.DateTime(), nullable=False),
    sa.Column("location", sa.String(length=200), nullable=True),
    sa.Column("attendees", sa.JSON(), nullable=False),
    sa.Column("tags", sa.JSON(), nullable=False),
    sa.Column("reminders", sa.JSON(), nullable=False),
    sa.Column("status", sa.String(length=16), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False),
    sa.CheckConstraint("status IN ('scheduled', 'ongoing', 'completed', 'cancelled')", name="ck_events_status"),
    sa.CheckConstraint("end_datetime > start_datetime", name="ck_events_date_order"),
  )
  op.create_table(
    "caldav_accounts",
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("name", sa.String(length=200), nullable=False),
    sa.Column("base_url", sa.String(length=500), nullable=False),
    sa.Column("calendar_url", sa.String(length=500), nullable=False),
    sa.Column("username", sa.String(length=200), nullable=False),
    sa.Column("password", sa.String(length=500), nullable=False),
    sa.Column("tags", sa.JSON(), nullable=False),
    sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
    sa.Column("sync_token", sa.String(length=500), nullable=True),
    sa.Column("last_synced_at", sa.DateTime(), nullable=True),
    sa.Column("last_sync_error", sa.String(length=2000), nullable=True),
    sa.Column("created_at", sa.DateTime(), nullable=False),
    sa.Column("updated_at", sa.DateTime(), nullable=False),
  )
  op.create_table(
    "caldav_event_links",
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("account_id", sa.String(), nullable=False),
    sa.Column("event_id", sa.String(), nullable=False),
    sa.Column("remote_uid", sa.String(length=500), nullable=False),
    sa.Column("remote_href", sa.String(length=1000), nullable=False),
    sa.Column("remote_etag", sa.String(length=200), nullable=True),
    sa.Column("sync_status", sa.String(length=32), nullable=False),
    sa.Column("last_synced_at", sa.DateTime(), nullable=True),
    sa.Column("last_sync_error", sa.String(length=2000), nullable=True),
    sa.Column("created_at", sa.DateTime(), nullable=False),
    sa.Column("updated_at", sa.DateTime(), nullable=False),
  )
  op.create_table(
    "notifications",
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("type", sa.String(length=16), nullable=False),
    sa.Column("message", sa.String(), nullable=False),
    sa.Column("entity_id", sa.String(), nullable=False),
    sa.Column("tags", sa.JSON(), nullable=False),
    sa.Column("timestamp", sa.DateTime(), nullable=False),
    sa.Column("read_status", sa.Boolean(), nullable=False, server_default=sa.text("0")),
    sa.Column("read_at", sa.DateTime(), nullable=True),
    sa.CheckConstraint("type IN ('alert', 'reminder', 'event')", name="ck_notifications_type"),
  )
  op.create_table(
    "agent_conversations",
    sa.Column("id", sa.String(), primary_key=True),
    sa.Column("message", sa.String(), nullable=False),
    sa.Column("response", sa.String(), nullable=False),
    sa.Column("action_type", sa.String(length=64), nullable=False),
    sa.Column("entity_type", sa.String(length=32), nullable=False),
    sa.Column("tags", sa.JSON(), nullable=False),
    sa.Column("context", sa.JSON(), nullable=False),
    sa.Column("created_at", sa.DateTime(), nullable=False),
  )

  op.create_index("idx_alerts_timestamp", "alerts", ["timestamp"])
  op.create_index("idx_alerts_severity", "alerts", ["severity"])
  op.create_index("idx_alerts_acknowledged", "alerts", ["acknowledged"])
  op.create_index("idx_alerts_tags", "alerts", ["tags"])
  op.create_index("idx_reminders_datetime", "reminders", ["datetime"])
  op.create_index("idx_reminders_status", "reminders", ["status"])
  op.create_index("idx_reminders_tags", "reminders", ["tags"])
  op.create_index("idx_events_start_datetime", "events", ["start_datetime"])
  op.create_index("idx_events_end_datetime", "events", ["end_datetime"])
  op.create_index("idx_events_status", "events", ["status"])
  op.create_index("idx_events_tags", "events", ["tags"])
  op.create_index("idx_caldav_accounts_is_active", "caldav_accounts", ["is_active"])
  op.create_index("idx_caldav_accounts_tags", "caldav_accounts", ["tags"])
  op.create_index("idx_caldav_event_links_account_id", "caldav_event_links", ["account_id"])
  op.create_index("idx_caldav_event_links_event_id", "caldav_event_links", ["event_id"])
  op.create_index("idx_caldav_event_links_remote_uid", "caldav_event_links", ["remote_uid"])
  op.create_index("idx_caldav_event_links_status", "caldav_event_links", ["sync_status"])
  op.create_index("idx_notifications_timestamp", "notifications", ["timestamp"])
  op.create_index("idx_notifications_type", "notifications", ["type"])
  op.create_index("idx_notifications_entity_id", "notifications", ["entity_id"])
  op.create_index("idx_notifications_read_status", "notifications", ["read_status"])
  op.create_index("idx_notifications_tags", "notifications", ["tags"])
  op.create_index("idx_agent_conversations_created_at", "agent_conversations", ["created_at"])


def downgrade() -> None:
  op.drop_index("idx_agent_conversations_created_at", table_name="agent_conversations")
  op.drop_index("idx_notifications_tags", table_name="notifications")
  op.drop_index("idx_notifications_read_status", table_name="notifications")
  op.drop_index("idx_notifications_entity_id", table_name="notifications")
  op.drop_index("idx_notifications_type", table_name="notifications")
  op.drop_index("idx_notifications_timestamp", table_name="notifications")
  op.drop_index("idx_events_tags", table_name="events")
  op.drop_index("idx_events_status", table_name="events")
  op.drop_index("idx_events_end_datetime", table_name="events")
  op.drop_index("idx_events_start_datetime", table_name="events")
  op.drop_index("idx_caldav_event_links_status", table_name="caldav_event_links")
  op.drop_index("idx_caldav_event_links_remote_uid", table_name="caldav_event_links")
  op.drop_index("idx_caldav_event_links_event_id", table_name="caldav_event_links")
  op.drop_index("idx_caldav_event_links_account_id", table_name="caldav_event_links")
  op.drop_index("idx_caldav_accounts_tags", table_name="caldav_accounts")
  op.drop_index("idx_caldav_accounts_is_active", table_name="caldav_accounts")
  op.drop_index("idx_reminders_tags", table_name="reminders")
  op.drop_index("idx_reminders_status", table_name="reminders")
  op.drop_index("idx_reminders_datetime", table_name="reminders")
  op.drop_index("idx_alerts_tags", table_name="alerts")
  op.drop_index("idx_alerts_acknowledged", table_name="alerts")
  op.drop_index("idx_alerts_severity", table_name="alerts")
  op.drop_index("idx_alerts_timestamp", table_name="alerts")
  op.drop_table("agent_conversations")
  op.drop_table("caldav_event_links")
  op.drop_table("caldav_accounts")
  op.drop_table("notifications")
  op.drop_table("events")
  op.drop_table("reminders")
  op.drop_table("alerts")
