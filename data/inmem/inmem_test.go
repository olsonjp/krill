package inmem

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestNewInMemoryDatastore(t *testing.T) {
	ds := NewInMemoryDatastore()
	assert.NotNil(t, ds)
}

func TestCreateIfNotExists(t *testing.T) {
	ds := NewInMemoryDatastore()
	assert.NotNil(t, ds)

	items := map[string]string{"test": "test"}
	err := ds.CreateIfNotExists(items)
	assert.NoError(t, err)
}
