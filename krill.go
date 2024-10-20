package main

import (
	"log"
	"net/http"

	"github.com/olsonjp/krill/internal/models"
	"github.com/olsonjp/krill/internal/services"
)

func main() {
	db, err := models.NewDatabase()
	if err != nil {
		log.Fatalf("failed to connect database: %v", err)
	}
	mux := services.SetupKrillRouter(db)
	log.Fatal(http.ListenAndServe(":8080", mux))
}
