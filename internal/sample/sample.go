package sample

import (
	"github.com/google/uuid"
)

type sample struct {
	name     string
	location string
	parent   uuid.UUID
}
