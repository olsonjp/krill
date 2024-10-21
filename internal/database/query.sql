-- name: GetSample :one
SELECT * FROM samples
WHERE id = ? LIMIT 1;

-- name: ListSamples :many
SELECT * FROM samples
ORDER BY id;