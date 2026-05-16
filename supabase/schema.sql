-- GT Trading Companion - Supabase Schema
-- Run this in the Supabase SQL Editor to set up the database

-- Watchlists table
CREATE TABLE IF NOT EXISTS watchlists (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT 'Default',
    tokens JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE(user_id, name)
);

-- Index for fast user lookups
CREATE INDEX IF NOT EXISTS idx_watchlists_user_id ON watchlists(user_id);
