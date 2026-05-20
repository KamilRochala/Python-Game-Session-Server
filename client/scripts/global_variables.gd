extends Node

var player_id: int = -1
var player_class: String = "None"
var player_name: String = "None"
var match_id: int = -1
var server_ip: String = ""

func get_base_url() -> String:
	return "http://" + server_ip + ":8080"
