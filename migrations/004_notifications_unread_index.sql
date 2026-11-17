CREATE INDEX IF NOT EXISTS notifications_unread_idx
    ON notifications(user_id, read_at)
    WHERE read_at IS NULL;
