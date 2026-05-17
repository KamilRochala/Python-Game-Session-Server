extends Control

const BASE_URL = "http://127.0.0.1:8000"

# Allocation Stats & Classes
var starter_points: int = 5
var attack_stat: int = 10
var defence_stat: int = 10

var classes: Array[String] = ["knight", "cleric"]
var current_class_index: int = 0

# Preload your small match UI card scene
@export var match_card_scene: PackedScene = preload("res://scenes/matchInfo.tscn")

# The UI Container where match cards will be instantiated (e.g., a VBoxContainer)
@onready var match_container: GridContainer = %GridContainer
@onready var poll_http_request: HTTPRequest = $HTTPRequest

# --- FIXED UNIQUE NODE REFERENCES ---
@onready var name_input: LineEdit = %NameInput
@onready var points_label: Label = %PointsLabel
@onready var class_portrait: TextureRect = %ClassPortrait  # Fixed spelling
@onready var def_label: Label = %DefenceRow/%DefLabel    # Explicitly pathing to avoid conflict
@onready var atk_label: Label = %AttackRow/%AtkLabel      # Assumes you rename this node to AtkLabel
@onready var log_message_label: Label = %LogMessageLabel
@onready var http_request: HTTPRequest = $HTTPRequest

# Track whether a poll request is actively in-flight
var is_polling: bool = false

func _ready() -> void:
	# Automatically bind buttons if they aren't bound in the inspector
	%DefMinusBtn.pressed.connect(_on_def_minus_btn_pressed)
	%DefPlusBtn.pressed.connect(_on_def_plus_btn_pressed)
	%AtkMinusBtn.pressed.connect(_on_atk_minus_btn_pressed)
	%AtkPlusBtn.pressed.connect(_on_atk_plus_btn_pressed)
	%PrevClassBtn.pressed.connect(_on_prev_class_btn_pressed)
	%NextClassBtn.pressed.connect(_on_next_class_btn_pressed)
	%CreateRoom.pressed.connect(_on_create_room_btn_pressed)
	
	update_ui()
	
	# 1. Connect the HTTP Request node's completion signal
	poll_http_request.request_completed.connect(_on_poll_request_completed)
	
	# 2. Setup the Polling Timer dynamically
	var poll_timer = Timer.new()
	poll_timer.wait_time = 2.0  # Poll every 2 seconds
	poll_timer.autostart = true
	poll_timer.one_shot = false
	
	# Connect the timer to fire the HTTP request
	poll_timer.timeout.connect(_fetch_matches)
	
	add_child(poll_timer)
	
	# Fire the first request immediately
	_fetch_matches()

func update_ui() -> void:
	if points_label: points_label.text = "Available points: " + str(starter_points)
	if def_label: def_label.text = str(defence_stat)
	if atk_label: atk_label.text = str(attack_stat)
	print("Current selected class: ", classes[current_class_index])
	GlobalVariables.player_class = classes[current_class_index]
	
	if name_input && name_input.text.strip_edges() != "":
		log_message_label.text = ""

# --- Class Swapping Controls ---
func _on_prev_class_btn_pressed() -> void:
	current_class_index = (current_class_index - 1 + classes.size()) % classes.size()
	update_ui()

func _on_next_class_btn_pressed() -> void:
	current_class_index = (current_class_index + 1) % classes.size()
	update_ui()

# --- Stat Altering Handlers ---
func _on_def_minus_btn_pressed() -> void:
	if defence_stat > 1:
		defence_stat -= 1
		starter_points += 1
		update_ui()

func _on_def_plus_btn_pressed() -> void:
	if starter_points > 0:
		defence_stat += 1
		starter_points -= 1
		update_ui()

func _on_atk_minus_btn_pressed() -> void:
	if attack_stat > 1:
		attack_stat -= 1
		starter_points += 1
		update_ui()

func _on_atk_plus_btn_pressed() -> void:
	if starter_points > 0:
		attack_stat += 1
		starter_points -= 1
		update_ui()

# --- Room / Player Creation API Trigger ---
func _on_create_room_btn_pressed() -> void:
	var player_name = name_input.text.strip_edges()
	
	if player_name == "":
		log_message_label.text = "Your player has no name!!!"
		return
	
	if player_name.length() > 10:
		log_message_label.text = "Your player name has more than 10 letters!!!"
		return
		
	var chosen_class = classes[current_class_index]
	var is_cleric = (chosen_class == "cleric")
	
	var player_payload = {
		"player_name": player_name,
		"player_class": chosen_class,
		"base_max_health": 120.0 if chosen_class == "knight" else 90.0,
		"base_damage": attack_stat,
		"base_healing_capacity": 8.0 if is_cleric else 0.0,
		"base_defence": defence_stat
	}
	
	var json_body = JSON.stringify(player_payload)
	var headers = ["Content-Type: application/json"]
	
	log_message_label.text = "Creating player profile..."
	
	var dynamic_request = HTTPRequest.new()
	add_child(dynamic_request)
	
	dynamic_request.request_completed.connect(_on_player_created)
	dynamic_request.request_completed.connect(func(_a,_b,_c,_d): dynamic_request.queue_free())
	
	dynamic_request.request(BASE_URL + "/addPlayer", headers, HTTPClient.METHOD_POST, json_body)

func _on_player_created(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	var response_string = body.get_string_from_utf8()
	
	if response_code in [200, 201]:
		var json = JSON.new()
		if json.parse(response_string) == OK:
			var player_data = json.get_data()
			var player_id = int(str(player_data.get("id")))
			log_message_label.text = "Player ready! Entering matchmaking slot..."
			
			var content_headers = ["Content-Type: application/json"]
			GlobalVariables.player_id = player_id
			http_request.request(BASE_URL + "/createMatch/" + str(player_id), content_headers, HTTPClient.METHOD_POST)
	else:
		print("Server Validation Error (422) Details: ", response_string)
		log_message_label.text = "Server Error: " + str(response_code)


# --- FIXED POLLING LOGIC ---

func _fetch_matches() -> void:
	# Use a simple boolean flag instead of checking HTTPClient status
	if is_polling:
		return
		
	var headers = ["Content-Type: application/json"]
	var error = poll_http_request.request(BASE_URL + "/getMatches", headers, HTTPClient.METHOD_GET)
	
	if error == OK:
		is_polling = true
	else:
		print("Failed to initiate HTTP request. Error code: ", error)

# Handles the server response
func _on_poll_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	# Always unlock the polling mechanism when a response cycles through
	is_polling = false

	if response_code != 200:
		print("Polling failed with response code: ", response_code)
		return
		
	var response_string = body.get_string_from_utf8()
	var json = JSON.new()
	
	if json.parse(response_string) == OK:
		var response_data = json.get_data()
		
		if typeof(response_data) == TYPE_ARRAY:
			_update_match_list(response_data)
		else:
			print("Server did not return an array of matches!")


# Instantiates and reconciles the UI elements seamlessly
func _update_match_list(matches: Array) -> void:
	# 1. Map existing UI cards by their match ID metadata
	var current_cards = {}
	for child in match_container.get_children():
		if child.has_meta("match_id"):
			var existing_id = child.get_meta("match_id")
			current_cards[existing_id] = child

	# 2. If the database is completely empty, wipe the UI immediately and exit
	if matches.is_empty():
		for card in current_cards.values():
			card.queue_free()
		return

	# 3. Track IDs coming in from the new server data
	var incoming_ids = []

	# 4. Handle additions and updates
	for match_data in matches:
		if typeof(match_data) != TYPE_DICTIONARY:
			continue
			
		var match_id = match_data.get("id")
		if match_id == null:
			continue
		
		incoming_ids.append(match_id)

		if current_cards.has(match_id):
			# Match already exists in UI! 
			var existing_card = current_cards[match_id]
			if existing_card.has_method("set_match_data"):
				existing_card.set_match_data(match_data)
		else:
			# Match is brand new! Instantiate and add it.
			if match_card_scene:
				var card_instance = match_card_scene.instantiate()
				
				# Tag the node with its ID so we can find it during the next poll loop
				card_instance.set_meta("match_id", match_id)
				
				match_container.add_child(card_instance)
				
				if card_instance.has_method("set_match_data"):
					card_instance.set_match_data(match_data)

	# 5. Handle removals safely using a clean boolean check
	for old_id in current_cards.keys():
		if incoming_ids.find(old_id) == -1:
			var card_to_remove = current_cards[old_id]
			if is_instance_valid(card_to_remove):
				card_to_remove.queue_free()


func _on_name_input_text_changed(new_text: String) -> void:
	GlobalVariables.player_name = new_text
