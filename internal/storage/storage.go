package storage

type freezer struct {
	name     string
	location string
	bays     int
}

func newFreezer(name string) *freezer {
	f := freezer{name: name}

	return &f
}

//func (f freezer) Store {}
