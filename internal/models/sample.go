package models

import (
	"encoding/json"
	"net/http"

	"gorm.io/gorm"
)

// Sample is a overarching sample designation that contains many aliquots
type Sample struct {
	gorm.Model
	Name  string  `json:"name"`
	Notes *string `json:"notes"`
}

func (s *Sample) SampleRecord(id int) (*Sample, error) {
	return &Sample{}, nil
}

func GetSample(w http.ResponseWriter, r *http.Request) {
	respondWithJSON(w, http.StatusOK, "getSample")
	w.Write([]byte("getSample"))
}

func respondWithJSON(w http.ResponseWriter, code int, payload interface{}) {
	response, _ := json.Marshal(payload)

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	w.Write(response)
}

// AliquotTypes are the types of aliquots that can be created, e.g. tissue, cell, etc.
type AliquotType struct {
	gorm.Model
	Description *string `json:"description,omitempty"`
}

// AliquotDisposition is the current status of a specific aliquot and is intended to drive check-in/check-out/destruction behavior
type AliquotDisposition struct {
	gorm.Model
	Name            string  `json:"name"`
	DispositionType string  `json:"disposition_type"`
	Description     *string `json:"description,omitempty"`
}

// Aliquots are individual units of Samples. They are the actual physical samples testing is conducted on
type Aliquot struct {
	gorm.Model
	SampleID      int     `json:"sample_id"`
	Quantity      int     `json:"quantity"`
	BoxID         int     `json:"box_id"`
	Row           int     `json:"row"`
	Column        int     `json:"column"`
	AliquotTypeID int     `json:"aliquot_type_id"`
	Passage       string  `json:"passage"`
	Notes         *string `json:"notes,omitempty"`
}
