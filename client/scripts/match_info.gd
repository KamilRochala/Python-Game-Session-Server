extends Control

## --- Configuration & API Endpoints ---
var BASE_URL: String:
	get:
		return GlobalVariables.get_base_url()

## --- UI Node References ---
@onready var match_name: Label = $Control/PanelContainer/Main/Labels/matchName
@onready var number_of_players: Label = $Control/PanelContainer/Main/Labels/numberOfPlayers
@onready var http_request: HTTPRequest = $HTTPRequest

## --- State Variables ---
var current_match_id: int = 0
var data: Dictionary = {}


## --- Core Data Initializer ---
func set_match_data(match_data: Dictionary) -> void:
	current_match_id = match_data.get("id", 0)
	
	# Connect the completion signal safely
	if not http_request.request_completed.is_connected(_on_get_data_completed):
		http_request.request_completed.connect(_on_get_data_completed)
	
	# Fetch host/owner name using player_1_id
	var host_id: int = match_data.get("player_1_id", 0)
	_make_get_request(host_id)
	
	# Calculate active players inside the slot array
	var player_ids: Array = [
		match_data.get("player_1_id"), 
		match_data.get("player_2_id"), 
		match_data.get("player_3_id"), 
		match_data.get("player_4_id")
	]

	var active_count: int = 0
	for player_id in player_ids:
		if player_id != null:
			active_count += 1

	number_of_players.text = str(active_count) + "/4 players"


func _make_get_request(player_id: int) -> void:
	var url := BASE_URL + "/player/" + str(player_id)
	var error := http_request.request(url)
	
	if error != OK:
		print("An error occurred while attempting the HTTP request code: ", error)


func _on_get_data_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS:
		print("Network error occurred.")
		return
		
	if response_code != 200:
		print("Server returned an error status: ", response_code)
		return
		
	var response_string := body.get_string_from_utf8()
	var json := JSON.new()
	
	if json.parse(response_string) == OK:
		data = json.get_data()
		match_name.text = str(data.get("player_name", "Unknown")) + "'s lobby"
	else:
		print("Failed to parse JSON response.")


## --- UI Button Actions ---
func _on_button_pressed() -> void:
	var player_name := ""
	if "player_name" in GlobalVariables:
		player_name = GlobalVariables.player_name.strip_edges()
		
	if player_name == "" or player_name == " ":
		print("Cannot join: Player name is empty!")
		return
		
	if GlobalVariables.get("player_id") > 0:
		_send_join_match_request(GlobalVariables.player_id)
	else:
		_create_player_before_joining()


## --- Network / API Methods ---
func _create_player_before_joining() -> void:
	print("Player profile not found. Registering to DB first...")
	
	# Safely read global fallbacks natively via Object.get(prop, default)
	var chosen_class: String = GlobalVariables.get("player_class")
	var max_health := 120.0 if chosen_class == "knight" else 90.0
	
	var player_payload := {
		"player_name": GlobalVariables.player_name.strip_edges(),
		"player_class": chosen_class,
		"base_max_health": max_health,
		"base_damage": 10,
		"base_healing_capacity": 0.0,
		"base_defence": 10
	}
	
	var json_body := JSON.stringify(player_payload)
	var headers := ["Content-Type: application/json"]
	
	var create_request := HTTPRequest.new()
	add_child(create_request)
	
	create_request.request_completed.connect(_on_create_player_completed)
	create_request.request_completed.connect(func(_a,_b,_c,_d): create_request.queue_free())
	
	var error := create_request.request(BASE_URL + "/addPlayer", headers, HTTPClient.METHOD_POST, json_body)
	if error != OK:
		print("Failed to initiate player creation request.")
		create_request.queue_free()


func _on_create_player_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if response_code not in [200, 201]:
		print("Server failed to register user profile. Response code: ", response_code)
		return

	var response_string := body.get_string_from_utf8()
	var json := JSON.new()
	if json.parse(response_string) == OK:
		var player_data: Dictionary = json.get_data()
		var player_id := int(str(player_data.get("id")))
		
		GlobalVariables.player_id = player_id
		print("Player profile successfully created with ID: ", player_id)
		
		_send_join_match_request(player_id)


func _send_join_match_request(player_id: int) -> void:
	print("Routing player ID ", player_id, " into the matchmaking queue...")
	
	var join_request := HTTPRequest.new()
	add_child(join_request)
	
	# Only connect the primary completion callback
	join_request.request_completed.connect(_on_join_match_completed)
	
	var url := BASE_URL + "/joinMatch/" + str(player_id)
	var headers := ["Content-Type: application/json"]
	
	var error := join_request.request(url, headers, HTTPClient.METHOD_POST)
	if error != OK:
		print("An error occurred while attempting to join the match: ", error)
		join_request.queue_free()


func _on_join_match_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	# 1. Get a local reference to the HTTPRequest node that fired this signal
	# (This allows us to clean it up safely no matter how the function exits)
	var sending_node: HTTPRequest = null
	for child in get_children():
		if child is HTTPRequest and child.is_connected("request_completed", _on_join_match_completed):
			sending_node = child
			break

	if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
		print("Server returned an error status context while joining: ", response_code)
		if sending_node: sending_node.queue_free()
		return
		
	var response_string := body.get_string_from_utf8()
	var json := JSON.new()
	
	if json.parse(response_string) == OK:
		var response_data: Dictionary = json.get_data()
		GlobalVariables.match_id = int(response_data.get("match_id", 0))
		print("Successfully Joined! Target Match ID Assigned: ", GlobalVariables.match_id)
		
		# 2. Clean up the node *before* switching scenes so it doesn't leak memory
		if sending_node: 
			sending_node.queue_free()
			
		# 3. Change scenes securely while this script's node is still firmly in the tree
		get_tree().change_scene_to_file("res://scenes/lobby.tscn")
	else:
		if sending_node: sending_node.queue_free()
