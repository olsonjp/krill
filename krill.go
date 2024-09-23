package main

import (
	"fmt"
	"io"
	"net/http"

	"github.com/olsonjp/krill/internal"
)

func main() {
    r := setupKrillRouter()
    http.ListenAndServe(":8080", r)
}
