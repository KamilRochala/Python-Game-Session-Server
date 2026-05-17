# match_display.gd
extends Control

@onready var matchName: Label = $Control/PanelContainer/Main/Labels/matchName
@onready var numberOfPlayers: Label = $Control/PanelContainer/Main/Labels/numberOfPlayers
@onready var http_request: HTTPRequest = $HTTPRequest

const BASE_URL = "http://127.0.0.1:8000"
var data
var current_match_id: int = 0

# A function to populate this specific card's data
func set_match_data(match_data: Dictionary) -> void:
	# Store the match ID so we know which match we are attempting to join later
	current_match_id = match_data.get("id", 0)
	
	# 1. Connect the completion signal safely (avoids duplicate connections)
	if not http_request.request_completed.is_connected(_on_get_data_completed):
		http_request.request_completed.connect(_on_get_data_completed)
	
	# 2. Fire off the request using the player ID from match_data
	var player_id = match_data.get("player_1_id", 0)
	_make_get_request(player_id)
	
	var counter: int = 0
	var player_ids = [
		match_data.get("player_1_id"), 
		match_data.get("player_2_id"), 
		match_data.get("player_3_id"), 
		match_data.get("player_4_id")
	]

	for player in player_ids:
		# Only count the player if the value is not null
		if player != null:
			counter += 1

	numberOfPlayers.text = str(counter) + "/4 players"

func _make_get_request(player_id: int) -> void:
	# Appending the player_id to the endpoint URL (e.g., "http://127.0.0.1:8000/player/42")
	var url = BASE_URL + "/player/" + str(player_id)
	
	# Send the request
	var error = http_request.request(url)
	
	if error != OK:
		print("An error occurred while attempting the HTTP request code: ", error)

func _on_get_data_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS:
		print("Network error occurred.")
		return
		
	if response_code != 200:
		print("Server returned an error status: ", response_code)
		return
		
	var response_string = body.get_string_from_utf8()
	var json = JSON.new()
	var parse_result = json.parse(response_string)
	
	if parse_result == OK:
		data = json.get_data()
		print("Data received successfully!", data)
		matchName.text = str(data.get("player_name", "Unknown")) + "'s lobby"
	else:
		print("Failed to parse JSON response.")

# --- ACTION: BUTTON PRESSED (JOIN / CREATE IF NEEDED) ---

func _on_button_pressed() -> void:
	# Validate if the player has entered a name before clicking join
	var player_name = GlobalVariables.player_name.strip_edges()
	if player_name == "":
		print("Cannot join: Player name is empty!")
		return
		
	# Check if the player already exists in the global variables scope
	if GlobalVariables.player_id != null && GlobalVariables.player_id > 0:
		# Player already exists, proceed directly to joining the match
		_send_join_match_request(GlobalVariables.player_id)
	else:
		# Player doesn't exist yet! We must register them into the DB first.
		_create_player_before_joining()

# --- BACKEND DB OPERATIONS ---

func _create_player_before_joining() -> void:
	print("Player profile not found. Registering to DB first...")
	
	# Generate payload based on global creation stats
	# (Reads fallback values if your stat variables are isolated to the other script)
	var player_payload = {
		"player_name": GlobalVariables.player_name.strip_edges(),
		"player_class": getattr(GlobalVariables, "player_class", "knight"),
		"base_max_health": 120.0 if getattr(GlobalVariables, "player_class", "knight") == "knight" else 90.0,
		"base_damage": 10, # Fallback default stat values
		"base_healing_capacity": 0.0,
		"base_defence": 10
	}
	
	var json_body = JSON.stringify(player_payload)
	var headers = ["Content-Type: application/json"]
	
	var create_request = HTTPRequest.new()
	add_child(create_request)
	
	create_request.request_completed.connect(_on_create_player_completed)
	create_request.request_completed.connect(func(_a,_b,_c,_d): create_request.queue_free())
	
	var error = create_request.request(BASE_URL + "/addPlayer", headers, HTTPClient.METHOD_POST, json_body)
	if error != OK:
		print("Failed to initiate player creation request.")
		create_request.queue_free()

func _on_create_player_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	var response_string = body.get_string_from_utf8()
	
	if response_code in [200, 201]:
		var json = JSON.new()
		if json.parse(response_string) == OK:
			var player_data = json.get_data()
			var player_id = int(str(player_data.get("id")))
			
			# Save profile context globally so we don't duplicate registration requests
			GlobalVariables.player_id = player_id
			print("Player profile successfully created with ID: ", player_id)
			
			# Proceed to final match routing phase
			_send_join_match_request(player_id)
	else:
		print("Server failed to register user profile: ", response_string)

func _send_join_match_request(player_id: int) -> void:
	print("Attempting to route player into Match ID: ", current_match_id)
	
	var join_request = HTTPRequest.new()
	add_child(join_request)
	
	join_request.request_completed.connect(_on_join_match_completed)
	join_request.request_completed.connect(func(_a, _b, _c, _d): join_request.queue_free())
	
	# Adjust this URL structure depending on whether your API requires the match ID explicitly
	var url = BASE_URL + "/joinMatch/" + str(player_id)
	var headers = ["Content-Type: application/json"]
	
	var error = join_request.request(url, headers, HTTPClient.METHOD_POST)
	if error != OK:
		print("An error occurred while attempting to join the match: ", error)
		join_request.queue_free()

func _on_join_match_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	if result != HTTPRequest.RESULT_SUCCESS:
		print("Network error occurred while joining.")
		return
		
	if response_code != 200:
		print("Server returned an error status context while joining: ", response_code)
		return
		
	print("Successfully Joined! Changing scenes...")
	# CHANGE SCENE HERE!!!!!!!!
	# get_tree().change_scene_to_file("res://scenes/game_lobby.tscn")

# Helper utility to read global variables safely if undefined
func getattr(obj: Object, property: String, default_val):
	if property in obj:
		return obj.get(property)
	return default_val
