package models

import "time"

// Sample is a overarching sample designation that contains many aliquots
type Sample struct {
	ID        int       `json:"id"`
	Name      string    `json:"name"`
	Notes     *string   `json:"notes"`
	CreatedAt time.Time `json:"created_at"`
	UpdatedAt time.Time `json:"updated_at"`
}

// AliquotType is the type of sample, e.g. tissue or cell
type AliquotType struct {
	ID          int       `json:"id"`
	Description *string   `json:"description,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
	UpdatedAt   time.Time `json:"updated_at"`
}

// AliquotDisposition is the current status of a specific aliquot and is intended to drive check-in/check-out/destruction behavior
type AliquotDisposition struct {
	ID              int       `json:"id"`
	Name            string    `json:"name"`
	DispositionType string    `json:"disposition_type"`
	Description     *string   `json:"description,omitempty"`
	CreatedAt       time.Time `json:"created_at"`
	UpdatedAt       time.Time `json:"updated_at"`
}

// Aliquots are individual units of Samples. They are the actual physical samples testing is conducted on
type Aliquot struct {
	ID            int       `json:"id"`
	SampleID      int       `json:"sample_id"`
	Quantity      int       `json:"quantity"`
	BoxID         int       `json:"box_id"`
	Row           int       `json:"row"`
	Column        int       `json:"column"`
	AliquotTypeID int       `json:"aliquot_type_id"`
	Passage       string    `json:"passage"`
	Notes         *string   `json:"notes,omitempty"`
	CreatedAt     time.Time `json:"created_at"`
	UpdatedAt     time.Time `json:"updated_at"`
}
