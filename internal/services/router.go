package services

import (
	"io"
	"log"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/olsonjp/krill/internal/database"
)

// SetupKrillRouter generates a new go-chi router and handles the middleware
// setup
func SetupKrillRouter(queries *database.Queries) *chi.Mux {
	r := chi.NewRouter()
	setupMiddlewares(r)

	r.HandleFunc("/", getHome(queries))
	// r.HandleFunc("/sample", GetSample)
	// r.HandleFunc("/sample/1", GetSampleById)
	return r
}

func getHome(queries *database.Queries) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		log.Println("root")
		io.WriteString(w, "Homepage goes here\n")
	}
}

func setupMiddlewares(r *chi.Mux) {
	r.Use(middleware.RealIP)
	r.Use(middleware.Heartbeat("/ping"))
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	r.Use(middleware.Timeout(60 * time.Second))
	r.Use(middleware.RequestID)
	r.Use(middleware.RedirectSlashes)
}
