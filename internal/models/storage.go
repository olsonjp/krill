package models

import "time"

// Site represents a physical locale where Samples are stored.
type Site struct {
	ID        int
	Name      string
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Location represents a specific building or office where Samples are stored.
type Location struct {
	ID        int
	Name      string
	SiteID    int
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Device represents a freezer or dewer in which Samples are stored.
type Device struct {
	ID        int
	Name      string
	SiteID    int
	Shelves   int
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Shelf represents a shelf in a freezer in which Samples are stored. Dewers will have a single shelf.
type Shelf struct {
	ID        int
	Name      string
	DeviceID  int
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Rack represents a rack in a freezer or dewer in which Samples are stored.
type Rack struct {
	ID        int
	Name      string
	ShelfID   int
	CreatedAt time.Time
	UpdatedAt time.Time
}

// Box represents a box in which aliquots are stored.
type Box struct {
	ID        int
	Name      string
	Rows      int
	Columns   int
	RackID    int
	CreatedAt time.Time
	UpdatedAt time.Time
}
