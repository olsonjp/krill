package data

// DB interface
type DataStore interface {
	// CreateIfNotExists creates a row, but only if it does not exist.
	CreateIfNotExists(items map[string]string) error
	// Read fetches a row by primary key
	// If minimumFields is empty or nil, all non-key fields would be fetched.
	Read(key string) (items map[string]string, err error)
	// Upsert updates some columns of a row, or creates a new one if it doesn't exist yet.
	Upsert(items map[string]string) error
	// Remove deletes a row
	Remove(keys []string) error

	// Shutdown finishes the connector to do clean up work
	Shutdown() error
}
