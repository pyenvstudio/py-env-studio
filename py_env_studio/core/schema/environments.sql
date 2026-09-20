-- SQL templates: environment registry queries.

-- name: get_env_id
SELECT env_id FROM environments WHERE env_name=?

-- name: create_environment
INSERT INTO environments (env_name, env_path, created_at) VALUES (?, ?, ?)
