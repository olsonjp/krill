package models

import (
	"gorm.io/gorm"
)

// Site represents a physical locale where Samples are stored.
type Site struct {
	gorm.Model
	Name string
}

// Location represents a specific building or office where Samples are stored.
type Location struct {
	gorm.Model
	Name   string
	SiteID int
}

// Device represents a freezer or dewer in which Samples are stored.
type Device struct {
	gorm.Model
	Name    string
	SiteID  int
	Shelves int
}

// Shelf represents a shelf in a freezer in which Samples are stored. Dewers will have a single shelf.
type Shelf struct {
	gorm.Model
	Name     string
	DeviceID int
}

// Rack represents a rack in a freezer or dewer in which Samples are stored.
type Rack struct {
	gorm.Model
	Name    string
	ShelfID int
}

// Box represents a box in which aliquots are stored.
type Box struct {
	gorm.Model
	Name    string
	Rows    int
	Columns int
	RackID  int
}
