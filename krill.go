package main

import (
	"log"
	"net/http"

	"github.com/olsonjp/krill/internal/database"
	"github.com/olsonjp/krill/internal/services"
)

func main() {
	db, err := database.NewDatabase()
	if err != nil {
		log.Fatalf("failed to connect database: %v", err)
	}
	defer db.Close()

	queries := database.New(db)

	mux := services.SetupKrillRouter(queries)
	log.Fatal(http.ListenAndServe(":8080", mux))
}
