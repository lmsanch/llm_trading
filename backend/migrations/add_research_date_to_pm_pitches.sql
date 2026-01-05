-- Migration: Add research_date column to pm_pitches table
-- Date: 2026-01-03
-- Description: Adds research_date column to associate PM pitches with specific research reports

-- Add research_date column if it doesn't exist
ALTER TABLE pm_pitches ADD COLUMN IF NOT EXISTS research_date TIMESTAMPTZ;

-- Create index for efficient querying by research_date
CREATE INDEX IF NOT EXISTS idx_pm_pitches_research_date ON pm_pitches(research_date);

-- Verify the column was added
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pm_pitches' AND column_name = 'research_date'
    ) THEN
        RAISE NOTICE 'Column research_date successfully added to pm_pitches table';
    ELSE
        RAISE EXCEPTION 'Failed to add research_date column';
    END IF;
END $$;

