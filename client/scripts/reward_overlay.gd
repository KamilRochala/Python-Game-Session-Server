extends PanelContainer

const BASE_URL = "http://127.0.0.1:8000"

@onready var choice_1 = %Choice1
@onready var choice_2 = %Choice2
@onready var choice_3 = %Choice3

@onready var choices = [choice_1, choice_2, choice_3]

var player_base_stats = {}
var loaded_textures = {}

func _ready() -> void:
	for i in range(choices.size()):
		var btn = choices[i].get_node("SelectButton")
		btn.pressed.connect(func(): _on_choice_selected(i + 1))

func fetch_and_show_rewards():
	if GlobalVariables.player_id == -1: return
	self.visible = true
	
	for choice in choices:
		choice.get_node("SelectButton").disabled = true
		choice.get_node("NameLabel").text = "Loading..."
		if choice.has_node("StatsLabel"):
			choice.get_node("StatsLabel").text = "..."
	
	var req_player = HTTPRequest.new()
	add_child(req_player)
	req_player.request_completed.connect(func(res, code, headers, body):
		if code == 200:
			var json = JSON.new()
			if json.parse(body.get_string_from_utf8()) == OK:
				player_base_stats = json.get_data()
				_fetch_reward_choices()
		req_player.queue_free()
	)
	req_player.request(BASE_URL + "/player/" + str(GlobalVariables.player_id))

func _fetch_reward_choices():
	var req = HTTPRequest.new()
	add_child(req)
	req.request_completed.connect(func(res, code, headers, body):
		if code == 200:
			var json = JSON.new()
			if json.parse(body.get_string_from_utf8()) == OK:
				var data = json.get_data()
				if typeof(data) == TYPE_ARRAY:
					_populate_choices(data)
		else:
			print("Error fetching rewards! Code: ", code, " Response: ", body.get_string_from_utf8())
			for choice in choices:
				choice.get_node("NameLabel").text = "Error Loading Rewards!"
				
		req.queue_free()
	)
	req.request(BASE_URL + "/rewardChoices/" + str(GlobalVariables.player_id))

func _populate_choices(data: Array):
	for i in range(min(data.size(), choices.size())):
		var choice_data = data[i]
		var item = choice_data.get("item_data", {})
		var item_type = choice_data.get("item_type", "")
		
		var ui_choice = choices[i]
		ui_choice.get_node("NameLabel").text = str(item.get("name", "Unknown"))
		
		var stat_text = ""
		
		var base_dmg = float(player_base_stats.get("base_damage", 0))
		var base_hp = float(player_base_stats.get("base_max_health", 0))
		var base_def = float(player_base_stats.get("base_defence", 0))
		
		var dmg_mult = 1.0
		var hp_mult = 1.0
		var def_mult = 1.0
		var heal_mult = 1.0
		
		# In a real scenario we'd fetch actual talisman multipliers, defaulting to 1.0
			
		if item_type == "weapon":
			var w_dmg = float(item.get("damage", 0))
			var w_heal = float(item.get("healing_capacity", 0))
			
			if w_dmg > 0:
				stat_text += "Damage: (%.1f + %.1f) * %.2f = %.1f\n" % [base_dmg, w_dmg, dmg_mult, (base_dmg + w_dmg) * dmg_mult]
			if w_heal > 0:
				var base_heal = float(player_base_stats.get("base_healing_capacity", 0))
				stat_text += "Heal: (%.1f + %.1f) * %.2f = %.1f\n" % [base_heal, w_heal, heal_mult, (base_heal + w_heal) * heal_mult]
				
		elif item_type == "armour":
			var a_def = float(item.get("defence_ammount", item.get("defence_amount", 0)))
			var a_hp = float(item.get("max_health_increase", 0))
			
			stat_text += "Def: (%.1f + %.1f) * %.2f = %.1f\n" % [base_def, a_def, def_mult, (base_def + a_def) * def_mult]
			stat_text += "MaxHP: (%.1f + %.1f) * %.2f = %.1f\n" % [base_hp, a_hp, hp_mult, (base_hp + a_hp) * hp_mult]
			
		elif item_type == "accessory":
			var mult = float(item.get("stat_multiplier", 1.0))
			var stat_name = str(item.get("what_stat_is_multiplied", "unknown")).capitalize()
			stat_text += "Multiplies %s by x%.2f\n" % [stat_name, mult]
			
		var sprite_path = item.get("sprite_path", "")
		var tex = null
		if sprite_path != "" and ResourceLoader.exists(sprite_path):
			tex = load(sprite_path)
			
		if tex:
			ui_choice.get_node("TextureBox").texture = tex
			
		loaded_textures[i + 1] = { "type": item_type, "texture": tex }
			
		if ui_choice.has_node("StatsLabel"):
			ui_choice.get_node("StatsLabel").text = stat_text
			
		ui_choice.get_node("SelectButton").disabled = false

func _on_choice_selected(index: int):
	for choice in choices:
		choice.get_node("SelectButton").disabled = true
		
	var req = HTTPRequest.new()
	add_child(req)
	var payload = {"selected_index": index}
	req.request_completed.connect(func(res, code, headers, body):
		if code == 200:
			self.visible = false
			var arena = get_parent()
			if arena.has_method("_on_reward_selected"):
				arena._on_reward_selected(loaded_textures.get(index))
		else:
			for choice in choices:
				choice.get_node("SelectButton").disabled = false
		req.queue_free()
	)
	req.request(BASE_URL + "/selectReward/" + str(GlobalVariables.player_id), ["Content-Type: application/json"], HTTPClient.METHOD_POST, JSON.stringify(payload))
