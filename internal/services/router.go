package services

import (
	"fmt"
	"io"
	"net/http"
	"time"

	"github.com/olsonjp/krill/internal/models"
	"gorm.io/gorm"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

// SetupKrillRouter generates a new go-chi router and handles the middleware
// setup
func SetupKrillRouter(db *gorm.DB) *chi.Mux {
	r := chi.NewRouter()
	r.Use(middleware.Timeout(60 * time.Second))
	// Setup the routes, middlewares, and handlers
	// r = setupMiddlewares(r)

	r.HandleFunc("/", getRoot)
	r.HandleFunc("/sample", models.GetSample)
	r.HandleFunc("/sample/1", models.GetSampleById)
	return r
}

//func setupMiddlewares(r *http.ServeMux) *http.ServeMux {
//	r.Use(middlewareOne)
//	r.Use(middlewareTwo)
//	return r
//}

func getRoot(w http.ResponseWriter, r *http.Request) {
	fmt.Println("root")
	io.WriteString(w, "Got Root?\n")
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
