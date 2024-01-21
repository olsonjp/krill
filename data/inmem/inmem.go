package inmem

import (
	"log"

	"github.com/hashicorp/go-memdb"
)

type InMemoryDatastore struct {
	database *memdb.MemDB
}

// NewInMemoryDatastore constructs a new go-memdb for non-durable storage
func NewInMemoryDatastore() InMemoryDatastore {
	krillSchema := &memdb.DBSchema{
		Tables: map[string]*memdb.TableSchema{
			"sample": {
				Name: "sample",
				Indexes: map[string]*memdb.IndexSchema{
					"id": {
						Name:    "id",
						Unique:  true,
						Indexer: &memdb.UUIDFieldIndex{Field: "id"},
					},
					"location": {
						Name:    "location",
						Unique:  true,
						Indexer: &memdb.StringFieldIndex{},
					},
				},
			},
			"person": {
				Name: "person",
				Indexes: map[string]*memdb.IndexSchema{
					"id": {
						Name:    "id",
						Unique:  true,
						Indexer: &memdb.UUIDFieldIndex{Field: "id"},
					},
					"name": {
						Name:    "name",
						Unique:  true,
						Indexer: &memdb.StringFieldIndex{},
					},
					"username": {
						Name:    "username",
						Unique:  true,
						Indexer: &memdb.StringFieldIndex{},
					},
				},
			},
		},
	}

	db, err := memdb.NewMemDB(krillSchema)

	if err != nil {
		log.Fatal("Couldn't create new database")
	}
	inmem := InMemoryDatastore{db}
	return inmem
}

func (db InMemoryDatastore) CreateIfNotExists(items map[string]string) error {

	return nil
}

// Read fetches a row by primary key
// If minimumFields is empty or nil, all non-key fields would be fetched.
func (db InMemoryDatastore) Read(key string) (items map[string]string, err error) {
	dummyReturn := map[string]string{"a": "a"}
	return dummyReturn, nil
}

// Upsert updates some columns of a row, or creates a new one if it doesn't exist yet.
func (db InMemoryDatastore) Upsert(items map[string]string) error {
	return nil
}

// Remove deletes a row
func (db InMemoryDatastore) Remove(keys []string) error {
	return nil
}

// Shutdown finishes the connector to do clean up work
func (db InMemoryDatastore) Shutdown() error {
	return nil
}
