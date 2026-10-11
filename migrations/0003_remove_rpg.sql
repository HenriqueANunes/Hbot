-- Remove os contadores do mini-RPG (gold/pp): comandos h.gold/h.pp tirados na v1.5.0.
ALTER TABLE usuarios DROP COLUMN IF EXISTS gold, DROP COLUMN IF EXISTS pp;
