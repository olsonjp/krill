package models

import (
	"gorm.io/driver/sqlite"
	"gorm.io/gorm"
)

func NewDatabase() (*gorm.DB, error) {
	db, err := gorm.Open(sqlite.Open("krill.db"), &gorm.Config{})
	if err != nil {
		return nil, err
	}

	return db, nil
}
