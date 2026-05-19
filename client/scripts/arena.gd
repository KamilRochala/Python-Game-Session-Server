extends Control

const BASE_URL = "http://127.0.0.1:8000"

# Preloaded textures
const KNIGHT_SPRITE = preload("res://assets/ui/knight-back.png")
const CLERIC_SPRITE = preload("res://assets/ui/cleric-back.png")

# --- PLACEHOLDER ENEMY TEXTURES ---
const DEFAULT_ENEMY_SPRITE = preload("res://assets/ui/temp.png") 

# Unique name layout label links for local client stats
@onready var current_hp_label = %CurrentHp
@onready var damage_label = %Damage
@onready var healing_capacity_label = %HealingCapacity
@onready var defence_label = %Defence

@onready var enemies_container = $GridContainer/TextureRect/Enemies
@onready var players_container = $GridContainer/Players/HBoxContainer

# Reference arrays for structural loops
@onready var player_nodes = [
	$GridContainer/Players/HBoxContainer/Player_1,
	$GridContainer/Players/HBoxContainer/Player_2,
	$GridContainer/Players/HBoxContainer/Player_3,
	$GridContainer/Players/HBoxContainer/Player_4
]

@onready var enemy_nodes = [
	$GridContainer/TextureRect/Enemies/Enemy_1,
	$GridContainer/TextureRect/Enemies/Enemy_2,
	$GridContainer/TextureRect/Enemies/Enemy_3,
	$GridContainer/TextureRect/Enemies/Enemy_4,
	$GridContainer/TextureRect/Enemies/Enemy_5
]

var poll_timer: Timer
var is_polling_match: bool = false
var current_combat_buttons_disabled: bool = true
var is_reward_phase: bool = false
var poll_enemy_requests_pending: int = 0
var poll_living_enemies: int = 0
var current_match_floor: int = -1
var has_selected_reward_for_floor: bool = false

func _ready() -> void:
	# Add Floor Display
	var floor_label = Label.new()
	floor_label.name = "FloorLabel"
	floor_label.text = "Floor: 1"
	floor_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_RIGHT, Control.PRESET_MODE_MINSIZE, 20)
	add_child(floor_label)

	# Setup poll timers
	poll_timer = Timer.new()
	poll_timer.wait_time = 2.0
	poll_timer.autostart = true
	poll_timer.timeout.connect(_poll_match_state)
	add_child(poll_timer)

	# Clean slate initialization: Hide everyone until server confirmation arrives
	for node in player_nodes:
		if is_instance_valid(node): node.visible = false
	for node in enemy_nodes:
		if is_instance_valid(node): node.visible = false

	_fetch_player_stats()
	_poll_match_state()


func _fetch_player_stats() -> void:
	if GlobalVariables.player_id == -1: return
	var req = HTTPRequest.new()
	add_child(req)
	req.request_completed.connect(func(res, code, headers, body):
		if code == 200:
			var json = JSON.new()
			if json.parse(body.get_string_from_utf8()) == OK:
				var p_data = json.get_data()
				if is_instance_valid(current_hp_label):
					current_hp_label.text = "Health: " + str(p_data.get("max_health", p_data.get("base_max_health", 0)))
					damage_label.text = "Damage: " + str(p_data.get("damage", p_data.get("base_damage", 0)))
					healing_capacity_label.text = "Healing Capacity: " + str(p_data.get("healing_capacity", p_data.get("base_healing_capacity", 0)))
					defence_label.text = "Defence: " + str(p_data.get("defence", p_data.get("base_defence", 0)))
		req.queue_free()
	)
	req.request(BASE_URL + "/player/" + str(GlobalVariables.player_id))


func _poll_match_state() -> void:
	if is_polling_match or GlobalVariables.match_id == -1: return
	
	var req = HTTPRequest.new()
	add_child(req)
	req.request_completed.connect(func(res, code, headers, body):
		is_polling_match = false
		if code == 200:
			var json = JSON.new()
			if json.parse(body.get_string_from_utf8()) == OK:
				var match_data = json.get_data()
				if typeof(match_data) == TYPE_DICTIONARY:
					var m_floor = int(match_data.get("floor_number", 1))
					if m_floor > current_match_floor:
						current_match_floor = m_floor
						has_selected_reward_for_floor = false
						var flbl = get_node_or_null("FloorLabel")
						if flbl: flbl.text = "Floor: " + str(m_floor)
						
					_process_match_party(match_data)
					_process_match_enemies(match_data)
					_synchronize_turn_ui(match_data)
		req.queue_free()
	)
	
	is_polling_match = true
	req.request(BASE_URL + "/getMatch/" + str(GlobalVariables.match_id), ["Content-Type: application/json"], HTTPClient.METHOD_GET)


func _process_match_party(match_data: Dictionary) -> void:
	var slots = ["player_1_id", "player_2_id", "player_3_id", "player_4_id"]
	for i in range(4):
		var slot_player_id = match_data.get(slots[i])
		var target_ui_node = player_nodes[i]
		
		if not is_instance_valid(target_ui_node): continue
			
		if slot_player_id != null:
			target_ui_node.visible = true
			_fetch_and_update_arena_player(int(slot_player_id), target_ui_node)
		else:
			target_ui_node.visible = false


func _fetch_and_update_arena_player(player_id: int, ui_node: VBoxContainer) -> void:
	var req = HTTPRequest.new()
	add_child(req)
	req.request_completed.connect(func(res, code, headers, body):
		if code == 200:
			var json = JSON.new()
			if json.parse(body.get_string_from_utf8()) == OK:
				var profile = json.get_data()
				if is_instance_valid(ui_node):
					var name_str = str(profile.get("player_name", "Unknown"))
					var max_hp = str(profile.get("base_max_health", "10"))
					var current_hp = str(profile.get("current_health", max_hp))
					
					ui_node.get_node("PlayerName").text = name_str
					ui_node.get_node("Health").text = "HP: " + current_health_format(current_hp) + "/" + max_hp
					
					var heal_btn = ui_node.get_node("HealBtn")
					heal_btn.visible = true
					heal_btn.disabled = current_combat_buttons_disabled
					for connection in heal_btn.pressed.get_connections():
						heal_btn.pressed.disconnect(connection.callable)
					heal_btn.pressed.connect(func(): _send_heal_request(player_id))
					
					var p_class = str(profile.get("player_class", "")).to_lower()
					var sprite_node = ui_node.get_node("PlayerSprite")
					sprite_node.texture = KNIGHT_SPRITE if p_class == "knight" else (CLERIC_SPRITE if p_class == "cleric" else null)
		req.queue_free()
	)
	req.request(BASE_URL + "/player/" + str(player_id), ["Content-Type: application/json"], HTTPClient.METHOD_GET)


func _process_match_enemies(match_data: Dictionary) -> void:
	if match_data.get("status") != "in_progress": return
	var enemy_ids = match_data.get("enemy_ids")
	if enemy_ids == null: enemy_ids = []
	
	poll_enemy_requests_pending = 0
	poll_living_enemies = 0
	
	for i in range(5):
		var target_ui_node = enemy_nodes[i]
		if not is_instance_valid(target_ui_node): continue
			
		if i < enemy_ids.size() and enemy_ids[i] != null:
			poll_enemy_requests_pending += 1
			_fetch_and_update_arena_enemy(int(enemy_ids[i]), target_ui_node)
		else:
			target_ui_node.visible = false
			
	if poll_enemy_requests_pending == 0:
		_check_combat_end()


func _fetch_and_update_arena_enemy(enemy_id: int, ui_node: VBoxContainer) -> void:
	var req = HTTPRequest.new()
	add_child(req)
	req.request_completed.connect(func(res, code, headers, body):
		if code == 200:
			var json = JSON.new()
			if json.parse(body.get_string_from_utf8()) == OK:
				var enemy_data = json.get_data()
				
				if is_instance_valid(ui_node):
					var current_hp : float = 0.0
					if enemy_data.has("current_hp"):
						current_hp = float(enemy_data["current_hp"])
					elif enemy_data.has("current_health"):
						current_hp = float(enemy_data["current_health"])

					var max_hp : float = float(enemy_data.get("max_hp", 10.0))
					var enemy_name : String = str(enemy_data.get("name", "Monster"))
					
					if current_hp <= 0:
						ui_node.visible = false
					else:
						ui_node.visible = true
						poll_living_enemies += 1
						ui_node.get_node("Health").text = enemy_name + " HP: " + str(int(current_hp)) + "/" + str(int(max_hp))
						
						var sprite_node = ui_node.get_node("EnemySprite")
						sprite_node.texture = DEFAULT_ENEMY_SPRITE
						
						var attack_btn = ui_node.get_node("AttackBtn")
						attack_btn.disabled = current_combat_buttons_disabled
						for connection in attack_btn.pressed.get_connections():
							attack_btn.pressed.disconnect(connection.callable)
							
						attack_btn.pressed.connect(func():
							_send_attack_request(enemy_id)
						)
						
					poll_enemy_requests_pending -= 1
					if poll_enemy_requests_pending == 0:
						_check_combat_end()
						
		req.queue_free()
	)
	req.request(BASE_URL + "/enemy/" + str(enemy_id), ["Content-Type: application/json"], HTTPClient.METHOD_GET)


func _check_combat_end():
	if poll_living_enemies == 0 and not is_reward_phase and not has_selected_reward_for_floor:
		is_reward_phase = true
		%TurnNotice.text = "Combat won! Choose your reward."
		_set_combat_buttons_disabled(true)
		%RewardOverlay.fetch_and_show_rewards()

func _on_reward_selected(reward_data):
	is_reward_phase = false
	has_selected_reward_for_floor = true
	if reward_data != null and reward_data.get("texture") != null:
		var type = reward_data.get("type", "")
		var tex = reward_data.get("texture")
		
		if type == "weapon":
			$GridContainer/ItemsPanel/VBoxContainer/Items/Weapon/TextureRect.texture = tex
		elif type == "armour":
			$GridContainer/ItemsPanel/VBoxContainer/Items/Armour/TextureRect.texture = tex
		elif type == "accessory":
			# For simplicity, assign to Accessory1
			$GridContainer/ItemsPanel/VBoxContainer/Items/Accessory1/TextureRect.texture = tex
			
	_fetch_player_stats()
	_poll_match_state()

# --- TURN SYNCHRONIZATION SYSTEM ---

func _synchronize_turn_ui(match_data: Dictionary) -> void:
	if is_reward_phase: return
	
	var turn_notice_label = %TurnNotice
	if not is_instance_valid(turn_notice_label): return

	var slots = ["player_1_id", "player_2_id", "player_3_id", "player_4_id"]
	var active_player_ids: Array = []
	for slot in slots:
		if match_data.get(slot) != null:
			active_player_ids.append(int(match_data.get(slot)))

	var enemy_ids: Array = match_data.get("enemy_ids", [])
	
	# If we selected a reward, but new enemies haven't spawned yet
	if has_selected_reward_for_floor and poll_living_enemies == 0:
		turn_notice_label.text = "Waiting for other players..."
		_set_combat_buttons_disabled(true)
		return
		
	var combat_order = active_player_ids + enemy_ids
	var current_turn_index = int(match_data.get("turn_index", 0))

	if current_turn_index >= combat_order.size():
		turn_notice_label.text = "Synchronizing round phase..."
		_set_combat_buttons_disabled(true)
		return

	var active_turn_entity_id = combat_order[current_turn_index]
	var is_player_turn = current_turn_index < active_player_ids.size()

	# 2. Check if the entity ID matching the active turn slot belongs to this local client player
	if is_player_turn and active_turn_entity_id == GlobalVariables.player_id:
		turn_notice_label.text = "YOUR TURN! Choose an action."
		_set_combat_buttons_disabled(false) # Unlock inputs
	elif is_player_turn:
		turn_notice_label.text = "Ally Turn Phase..."
		_set_combat_buttons_disabled(true)  # Lock inputs
	else:
		turn_notice_label.text = "ENEMY TURN PHASE - Watch out!"
		_set_combat_buttons_disabled(true)  # Lock inputs


func _set_combat_buttons_disabled(should_disable: bool) -> void:
	current_combat_buttons_disabled = should_disable
	# Toggle attack buttons on all visible enemies
	for enemy_node in enemy_nodes:
		if is_instance_valid(enemy_node) and enemy_node.visible:
			enemy_node.get_node("AttackBtn").disabled = should_disable

	# Toggle heal buttons on all visible friendly players
	for player_node in player_nodes:
		if is_instance_valid(player_node) and player_node.visible:
			player_node.get_node("HealBtn").disabled = should_disable


# --- ACTIONS & NETWORK REQUESTS ---

func _send_attack_request(target_enemy_id: int) -> void:
	var attack_req = HTTPRequest.new()
	add_child(attack_req)
	
	var actual_damage: float = 10.0
	if is_instance_valid(damage_label):
		var text_val = damage_label.text.replace("Damage: ", "")
		if text_val.is_valid_float():
			actual_damage = float(text_val)
	
	var payload = {
		"enemy_id": target_enemy_id,
		"damage_amount": actual_damage 
	}
	
	attack_req.request_completed.connect(func(res, code, headers, body):
		if code == 200:
			print("Combat registration complete: ", body.get_string_from_utf8())
			_poll_match_state() 
		else:
			print("Combat registration failed! Code: ", code, " Body: ", body.get_string_from_utf8())
		attack_req.queue_free()
	)
	
	var target_url = BASE_URL + "/attackEnemy/" + str(GlobalVariables.match_id)
	attack_req.request(target_url, ["Content-Type: application/json"], HTTPClient.METHOD_POST, JSON.stringify(payload))


func _send_heal_request(target_id: int) -> void:
	if GlobalVariables.match_id == -1 or GlobalVariables.player_id == -1: return
	var heal_req = HTTPRequest.new()
	add_child(heal_req)
	var payload = {"healer_id": GlobalVariables.player_id, "target_player_id": target_id}
	
	heal_req.request_completed.connect(func(res, code, headers, body):
		if code == 200:
			_poll_match_state()
		heal_req.queue_free()
	)
	heal_req.request(BASE_URL + "/healPlayer/" + str(GlobalVariables.match_id), ["Content-Type: application/json"], HTTPClient.METHOD_POST, JSON.stringify(payload))


func current_health_format(val) -> String:
	return str(int(float(val)))
