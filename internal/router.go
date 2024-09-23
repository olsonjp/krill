package internal

import (
	"fmt"
	"io"
	"net/http"
)

func setupKrillRouter() *http.ServeMux {
	r := http.NewServeMux()
	r.HandleFunc("/", getRoot)
	return r
}

func getRoot(w http.ResponseWriter, r *http.Request) {
	fmt.Println("root")
	io.WriteString(w, "Got Root?\n")
}
