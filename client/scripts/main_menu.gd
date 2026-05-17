extends Control

## --- Configuration & Preloads ---
const BASE_URL: String = "http://127.0.0.1:8000"

@export var match_card_scene: PackedScene = preload("res://scenes/matchInfo.tscn")

const KNIGHT_SPRITE = preload("res://assets/ui/knight.png")
const CLERIC_SPRITE = preload("res://assets/ui/cleric.png")

## --- Stats & Classes ---
var starter_points: int = 5
var attack_stat: int = 10
var defence_stat: int = 10

var classes: Array[String] = ["knight", "cleric"]
var current_class_index: int = 0
var is_polling: bool = false

## --- UI & Network Node References ---
@onready var match_container: GridContainer = %GridContainer
@onready var poll_http_request: HTTPRequest = $HTTPRequest

@onready var name_input: LineEdit = %NameInput
@onready var points_label: Label = %PointsLabel
@onready var class_portrait: TextureRect = %ClassPortrait 
@onready var class_description: Label = %ClassDescription
@onready var def_label: Label = %DefenceRow/%DefLabel    
@onready var atk_label: Label = %AttackRow/%AtkLabel      
@onready var log_message_label: Label = %LogMessageLabel


## --- Lifecycle Methods ---
func _ready() -> void:
	# UI Connections
	%DefMinusBtn.pressed.connect(_on_def_minus_btn_pressed)
	%DefPlusBtn.pressed.connect(_on_def_plus_btn_pressed)
	%AtkMinusBtn.pressed.connect(_on_atk_minus_btn_pressed)
	%AtkPlusBtn.pressed.connect(_on_atk_plus_btn_pressed)
	%PrevClassBtn.pressed.connect(_on_prev_class_btn_pressed)
	%NextClassBtn.pressed.connect(_on_next_class_btn_pressed)
	%CreateRoom.pressed.connect(_on_create_room_btn_pressed)
	%NameInput.text_changed.connect(_on_name_input_text_changed)
	
	update_ui()
	
	# Polling Setup
	poll_http_request.request_completed.connect(_on_poll_request_completed)
	
	var poll_timer := Timer.new()
	poll_timer.wait_time = 2.0
	poll_timer.autostart = true
	poll_timer.one_shot = false
	poll_timer.timeout.connect(_fetch_matches)
	add_child(poll_timer)
	
	_fetch_matches()


func update_ui() -> void:
	if points_label: points_label.text = "Available points: " + str(starter_points)
	if def_label: def_label.text = str(defence_stat)
	if atk_label: atk_label.text = str(attack_stat)
	
	GlobalVariables.player_class = classes[current_class_index]
	
	if class_portrait:
		if GlobalVariables.player_class == "knight":
			class_portrait.texture = KNIGHT_SPRITE
			if class_description: class_description.text = "Deals big damage and wields blunt weapons"
		elif GlobalVariables.player_class == "cleric":
			class_portrait.texture = CLERIC_SPRITE
			if class_description: class_description.text = "Heals for more and wields magic weapons"
	
	if name_input and name_input.text.strip_edges() != "":
		log_message_label.text = ""


## --- Class Swapping Controls ---
func _on_prev_class_btn_pressed() -> void:
	current_class_index = (current_class_index - 1 + classes.size()) % classes.size()
	update_ui()


func _on_next_class_btn_pressed() -> void:
	current_class_index = (current_class_index + 1) % classes.size()
	update_ui()


## --- Stat Altering Handlers ---
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


## --- Network Handlers & API Triggers ---
func _on_create_room_btn_pressed() -> void:
	var player_name := name_input.text.strip_edges()
	
	if player_name == "":
		log_message_label.text = "Your player has no name!!!"
		return
	
	if player_name.length() > 10:
		log_message_label.text = "Your player name has more than 10 letters!!!"
		return
		
	var chosen_class := classes[current_class_index]
	var is_cleric := (chosen_class == "cleric")
	
	var player_payload := {
		"player_name": player_name,
		"player_class": chosen_class,
		"base_max_health": 120.0 if chosen_class == "knight" else 90.0,
		"base_damage": attack_stat,
		"base_healing_capacity": 8.0 if is_cleric else 0.0,
		"base_defence": defence_stat
	}
	
	var json_body := JSON.stringify(player_payload)
	var headers := ["Content-Type: application/json"]
	
	log_message_label.text = "Creating player profile..."
	
	var dynamic_request := HTTPRequest.new()
	add_child(dynamic_request)
	
	dynamic_request.request_completed.connect(_on_player_created)
	dynamic_request.request_completed.connect(func(_a,_b,_c,_d): dynamic_request.queue_free())
	
	dynamic_request.request(BASE_URL + "/addPlayer", headers, HTTPClient.METHOD_POST, json_body)


func _on_player_created(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	var response_string := body.get_string_from_utf8()
	
	if response_code in [200, 201]:
		var json := JSON.new()
		if json.parse(response_string) == OK:
			var player_data: Dictionary = json.get_data()
			var player_id := int(str(player_data.get("id")))
			
			log_message_label.text = "Player ready! Entering matchmaking slot..."
			GlobalVariables.player_id = player_id
			
			# Dynamic request for Match Creation
			var match_create_req := HTTPRequest.new()
			add_child(match_create_req)
			
			var content_headers := ["Content-Type: application/json", "Content-Length: 0"]
			match_create_req.request_completed.connect(_on_match_created)
			match_create_req.request_completed.connect(func(_a,_b,_c,_d): match_create_req.queue_free())
			
			match_create_req.request(BASE_URL + "/createMatch/" + str(player_id), content_headers, HTTPClient.METHOD_POST, "")
	else:
		print("Server Validation Error Details: ", response_string)
		log_message_label.text = "Server Error: " + str(response_code)


func _on_match_created(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	if response_code in [200, 201]:
		var response_string := body.get_string_from_utf8()
		var json := JSON.new()
		if json.parse(response_string) == OK:
			var match_data: Dictionary = json.get_data() # Pulls the actual JSON parsed dict data
			GlobalVariables.match_id = int(str(match_data.get("id")))
			
			print("Match created successfully! Saved Match ID: ", GlobalVariables.match_id)
			get_tree().change_scene_to_file("res://scenes/lobby.tscn")


## --- Matchmaking Polling Logic ---
func _fetch_matches() -> void:
	if is_polling:
		return
		
	var headers := ["Content-Type: application/json"]
	var error := poll_http_request.request(BASE_URL + "/getMatches", headers, HTTPClient.METHOD_GET)
	
	if error == OK:
		is_polling = true
	else:
		print("Failed to initiate HTTP request. Error code: ", error)


func _on_poll_request_completed(result: int, response_code: int, headers: PackedStringArray, body: PackedByteArray) -> void:
	is_polling = false

	if response_code != 200:
		print("Polling failed with response code: ", response_code)
		return
		
	var response_string := body.get_string_from_utf8()
	var json := JSON.new()
	
	if json.parse(response_string) == OK:
		var response_data = json.get_data()
		if typeof(response_data) == TYPE_ARRAY:
			_update_match_list(response_data)
		else:
			print("Server did not return an array of matches!")


func _update_match_list(matches: Array) -> void:
	var current_cards := {}
	for child in match_container.get_children():
		if child.has_meta("match_id"):
			current_cards[child.get_meta("match_id")] = child

	if matches.is_empty():
		for card in current_cards.values():
			card.queue_free()
		return

	var incoming_ids := []

	for match_data in matches:
		if typeof(match_data) != TYPE_DICTIONARY:
			continue
			
		var match_id = match_data.get("id")
		if match_id == null:
			continue
		
		incoming_ids.append(match_id)

		if current_cards.has(match_id):
			var existing_card = current_cards[match_id]
			if existing_card.has_method("set_match_data"):
				existing_card.set_match_data(match_data)
		else:
			if match_card_scene:
				var card_instance = match_card_scene.instantiate()
				card_instance.set_meta("match_id", match_id)
				match_container.add_child(card_instance)
				
				if card_instance.has_method("set_match_data"):
					card_instance.set_match_data(match_data)

	# Clean removal checks using native 'not in' array syntax
	for old_id in current_cards.keys():
		if old_id not in incoming_ids:
			var card_to_remove = current_cards[old_id]
			if is_instance_valid(card_to_remove):
				card_to_remove.queue_free()


## --- Text Input Handlers ---
func _on_name_input_text_changed(new_text: String) -> void:
	GlobalVariables.player_name = new_text
	if new_text.strip_edges() != "" and new_text.length() <= 10:
		log_message_label.text = ""
