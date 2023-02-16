package main

import (
	"encoding/json"
	"bytes"
	"log"
	"os"
	"os/user"
	"net/http"

	"github.com/zcalusic/sysinfo"
)

func main() {
	current, err := user.Current()
	if err != nil {
		log.Fatal(err)
	}

	if current.Uid != "0" {
		log.Fatal("requires superuser privilege")
	}

	var si sysinfo.SysInfo

	si.GetSysInfo()

	data, err := json.MarshalIndent(&si, "", "  ")
	if err != nil {
		log.Fatal(err)
	}

	myhostname, error := os.Hostname()
	httpposturl := "http://localhost:8080/update?hostname=" + myhostname
	request, error := http.NewRequest("POST", httpposturl, bytes.NewBuffer(data))
	request.Header.Set("Content-Type", "application/json; charset=UTF-8")
	client := &http.Client{}
	response, error := client.Do(request)
	if error != nil {
		panic(error)
	}
	defer response.Body.Close()
}
