import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import os
from dotenv import load_dotenv
import random
from typing import List, Dict, Any
from math import sin

from classes.weapon import Weapon, WeaponType
from classes.armour import Armour
from classes.accessory import Accessory, Stat
from classes.player import Player

from classes.enemy import Enemy

load_dotenv()

app = FastAPI()

class SelectionRequest(BaseModel):
    selected_index: int

def generate_reward(current_floor: int, is_healer: bool):
    reward_type = random.choice(["weapon", "armour", "accessory"])

    modifier_name = ["Big", "Small", "Sharp", "Dull", "Rusty", "Shiny", "Ancient", "Sturdy"]

    multiplier = (current_floor ** 0.6) * (0.5 + 0.5 * (abs(sin(current_floor))))

    if reward_type == "weapon":
        weapon_name = ["Mace", "Sword", "Whip", "Greatsword", "Lance", "Spear", "Axe"]
        healer_name = ["Wand", "Staff", "Spellbook", "Spell"]
        
        random_mod = random.choice(modifier_name)
        
        if is_healer:
            name = random.choice(healer_name)
            item = Weapon(
                name=f"{random_mod} {name}",
                sprite_path=f"res://assets/weapons/{name.lower()}.png",
                floor_multiplier=int(multiplier) if int(multiplier) > 0 else 1,
                damage=int(random.randint(1, 5) * multiplier),
                healing_capacity=int(random.randint(5, 12) * multiplier),
                weapon_type=WeaponType.CLERIC
            )
        else:
            name = random.choice(weapon_name)
            item = Weapon(
                name=f"{random_mod} {name}",
                sprite_path=f"res://assets/weapons/{name.lower()}.png",
                floor_multiplier=int(multiplier) if int(multiplier) > 0 else 1,
                damage=int(random.randint(5, 15) * multiplier),
                healing_capacity=0,
                weapon_type=WeaponType.KNIGHT
            )
        return item, "weapon"

    elif reward_type == "armour":
        armour_names = ["Chestplate", "Chainmail", "Robes", "Tunic"]
        name = random.choice(armour_names)
        item = Armour(
            name=f"{random.choice(modifier_name)} {name}",
            sprite_path=f"res://assets/armour/{name.lower()}.png",
            floor_multiplier=int(multiplier) if int(multiplier) > 0 else 1,
            defence_ammount=int(random.randint(1, 10) * multiplier),
            max_health_increase=int(random.randint(5, 20) * multiplier)
        )
        return item, "armour"

    else:
        acc_names = ["Ring", "Necklace", "Amulet", "Bracelet"]
        name = random.choice(acc_names)
        item = Accessory(
            name=f"{random.choice(modifier_name)} {name}",
            sprite_path=f"res://assets/accessories/{name.lower()}.png",
            floor_multiplier=int(multiplier) if int(multiplier) > 0 else 1,
            what_stat_is_multiplied=random.choice(list(Stat)),
            stat_multiplier=round(random.uniform(1.05, 1.5), 2)
        )
        return item, "accessory"

def generate_enemies(current_floor: int, player_name: str):
    enemy_types = ["Slime", "Gremlin", "Skeleton", "Miner knight", "Rat man", "Wandering angel", "Mudman", "Frog sentiniel", "Lost paladin"]
    list_of_enemies = []

    number_of_enemies = random.randint(1, 5)
    multiplier = (current_floor**0.7)
    #random.choice

    for number in range(number_of_enemies):
        temp_enemy = Enemy(
            max_hp=random.randint(15, 25) * multiplier, 
            damage=random.randint(5,10) * multiplier, 
            armour=int(random.randint(2,4) * multiplier), 
            name="Trywialne" if player_name == "Trivial" else random.choice(enemy_types)
        )
        list_of_enemies.append(temp_enemy)
        
    return list_of_enemies

def advance_turn_system(match_id: int, cur):
    """
    Moves the turn index forward. If the next slot belongs to an enemy, 
    the enemy executes an attack instantly, and the loop continues 
    until it lands on a valid player's turn.
    """
    # 1. Fetch current match state
    cur.execute("SELECT * FROM matches WHERE id = %s", (match_id,))
    match = cur.fetchone()
    if not match:
        return

    # 2. Build the turn order list of living/valid entities
    # Players first, then enemies
    players = [match["player_1_id"], match["player_2_id"], match["player_3_id"], match["player_4_id"]]
    active_player_ids = [pid for pid in players if pid is not None]
    
    enemy_ids = match.get("enemy_ids") or []
    
    # Filter out dead enemies
    living_enemy_ids = []
    if enemy_ids:
        cur.execute("SELECT id FROM enemies WHERE id = ANY(%s) AND current_hp > 0 ORDER BY id ASC", (enemy_ids,))
        living_enemy_ids = [row["id"] for row in cur.fetchall()]

    # If all enemies are dead, combat is over!
    if not living_enemy_ids:
        return

    # Total combatants order array
    combat_order = [("player", pid) for pid in active_player_ids] + [("enemy", eid) for eid in living_enemy_ids]
    
    # Calculate next index position safely loop-wrapped
    current_index = match.get("turn_index")
    if current_index is None:
        current_index = 0
    next_index = (current_index + 1) % len(combat_order)
    
    # Update match with next index temporarily to prevent race conditions
    cur.execute("UPDATE matches SET turn_index = %s WHERE id = %s", (next_index, match_id))
    current_entity_type, current_entity_id = combat_order[next_index]

    # 3. If the current entity is an ENEMY, automate its attack turn!
    if current_entity_type == "enemy":
        # Fetch enemy attack power
        cur.execute("SELECT name, damage FROM enemies WHERE id = %s", (current_entity_id,))
        enemy = cur.fetchone()
        
        if enemy:
            # Pick a random player to target
            target_player_id = random.choice(active_player_ids)
            
            # Fetch target player current health
            cur.execute("SELECT current_health, player_name FROM players WHERE id = %s", (target_player_id,))
            player_row = cur.fetchone()
            
            if player_row:
                new_hp = max(0.0, float(player_row["current_health"] or 0) - float(enemy["damage"]))
                
                # Deal damage to player row
                cur.execute("UPDATE players SET current_health = %s WHERE id = %s", (new_hp, target_player_id))
                print(f"Enemy {enemy['name']} auto-attacked {player_row['player_name']} for {enemy['damage']} DMG.")
        
        # Recurse: Move to the next turn automatically!
        advance_turn_system(match_id, cur)



# Connection settings
DB_PARAMS = {
    "host": os.getenv('DB_HOST'),
    "database":  os.getenv('DB_NAME'),
    "user": os.getenv('DB_USER'),
    "password": os.getenv('DB_PASSWORD'),
    "port": os.getenv('DB_PORT')
}

def get_db_connection():
    return psycopg2.connect(**DB_PARAMS)

@app.get("/player/{player_id}")
def get_match(player_id: int):
    # Connecting to the db
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = "SELECT * FROM players WHERE id = %s"
        cur.execute(query, (player_id,))
        match = cur.fetchone()

        if not match:
            raise HTTPException(status_code=404, detail="Player not found")
            
        return match
    finally:
        cur.close()
        conn.close()

@app.post("/addPlayer")
def add_player(player: Player):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        params = {
            "name": player.player_name,
            "class": player.player_class.value,
            "base_max_health": player.base_max_health,
            "base_damage": player.base_damage,
            "base_healing_capacity": player.base_healing_capacity,
            "base_defence": player.base_defence,

            "max_health": player.max_health,
            "damage": player.damage,
            "healing_capacity": player.healing_capacity,
            "defence": player.defence,
            "current_health": player.current_health
        }

        query_add_player = """
        INSERT INTO public.players(
        player_name, player_class, base_max_health, max_health, current_health, base_damage, damage, base_healing_capacity, healing_capacity, base_defence, defence)
        VALUES (%(name)s, %(class)s, %(base_max_health)s, %(max_health)s, %(current_health)s, %(base_damage)s, %(damage)s, %(base_healing_capacity)s, %(healing_capacity)s, %(base_defence)s, %(defence)s) RETURNING *;
        """

        cur.execute(query_add_player, params)
        player_table = cur.fetchone()

        if not player_table:
            raise HTTPException(status_code=404, detail="Player not found")
        
        conn.commit()
            
        return player_table

    finally:
        cur.close()
        conn.close()

#@app.

@app.get("/rewardChoices/{player_id}")
def get_reward_choices(player_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check current floor by finding player's match
        query_check_player_match = """
        SELECT m.id, m.status 
        FROM matches m 
        WHERE m.player_1_id = %s OR m.player_2_id = %s OR m.player_3_id = %s OR m.player_4_id = %s
        """
        cur.execute(query_check_player_match, (player_id, player_id, player_id, player_id))
        match_row = cur.fetchone()
        
        # We assume floor is tied to match ID for now or defaults to 1
        current_floor = match_row["id"] if match_row else 1

        query_check_player_class = """
        SELECT player_class FROM players WHERE id = %s
        """
        cur.execute(query_check_player_class, (player_id,))
        player_row = cur.fetchone()
        
        if not player_row:
            raise HTTPException(status_code=404, detail="Player not found")
            
        is_healer = player_row["player_class"].lower() == "cleric"
        
        # Clear any existing choices for this player
        cur.execute("DELETE FROM pending_reward_choices WHERE player_id = %s", (player_id,))
        
        choices_response = []
        for i in range(1, 4):
            item, i_type = generate_reward(current_floor, is_healer)
            
            if i_type == "weapon":
                cur.execute("""
                INSERT INTO pending_reward_choices 
                (player_id, choice_index, item_type, name, sprite_path, damage, healing_capacity, weapon_class)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (player_id, i, i_type, item.name, item.sprite_path, item.damage, item.healing_capacity, item.weapon_type.value))
                
            elif i_type == "armour":
                cur.execute("""
                INSERT INTO pending_reward_choices 
                (player_id, choice_index, item_type, name, sprite_path, defence_amount, max_health_increase)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (player_id, i, i_type, item.name, item.sprite_path,item.defence_ammount, item.max_health_increase))
                
            elif i_type == "accessory":
                cur.execute("""
                INSERT INTO pending_reward_choices 
                (player_id, choice_index, item_type, name, sprite_path, stat_to_multiply, stat_multiplier)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (player_id, i, i_type, item.name, item.sprite_path, item.what_stat_is_multiplied.value, item.stat_multiplier))

            choices_response.append({
                "choice_index": i,
                "item_type": i_type,
                "item_data": item.model_dump()
            })
            
        conn.commit()
        return choices_response

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

def recalculate_player_stats(player_id: int, cur):
    cur.execute("SELECT * FROM players WHERE id = %s", (player_id,))
    p = cur.fetchone()
    if not p: return

    # get weapon
    w_dmg = 0
    w_heal = 0
    if p.get("weapon_id"):
        cur.execute("SELECT damage, healing_capacity FROM weapons WHERE item_id = %s", (p["weapon_id"],))
        w = cur.fetchone()
        if w:
            w_dmg = w["damage"]
            w_heal = w["healing_capacity"]

    # get armour
    a_def = 0
    a_hp = 0
    if p.get("armour_id"):
        cur.execute("SELECT defence_amount, max_health_increase FROM armours WHERE item_id = %s", (p["armour_id"],))
        a = cur.fetchone()
        if a:
            a_def = a["defence_amount"]
            a_hp = a["max_health_increase"]

    # get accessories
    mult_dmg = 1.0
    mult_hp = 1.0
    mult_heal = 1.0
    add_def = 0.0

    for acc_id in [p.get("acc_slot_1"), p.get("acc_slot_2"), p.get("acc_slot_3")]:
        if acc_id:
            cur.execute("SELECT stat_to_multiply, stat_multiplier FROM accessories WHERE item_id = %s", (acc_id,))
            acc = cur.fetchone()
            if acc:
                stat = acc["stat_to_multiply"]
                val = acc["stat_multiplier"]
                if stat == "dmg": mult_dmg *= val
                elif stat == "maxhp": mult_hp *= val
                elif stat == "hc": mult_heal *= val
                elif stat == "def": add_def += val

    old_max_hp = p["max_health"]
    
    new_dmg = (p["base_damage"] + w_dmg) * mult_dmg
    new_hp = (p["base_max_health"] + a_hp) * mult_hp
    new_heal = (p["base_healing_capacity"] + w_heal) * mult_heal
    new_def = p["base_defence"] + a_def + add_def
    
    current_hp = float(p["current_health"]) if p.get("current_health") is not None else float(p["base_max_health"])
    if new_hp > old_max_hp:
        current_hp += (new_hp - old_max_hp)
    
    if current_hp > new_hp:
        current_hp = new_hp
    
    cur.execute('''
        UPDATE players 
        SET damage = %s, max_health = %s, healing_capacity = %s, defence = %s, current_health = %s
        WHERE id = %s
    ''', (new_dmg, new_hp, new_heal, new_def, current_hp, player_id))


@app.post("/selectReward/{player_id}")
def select_reward(player_id: int, req: SelectionRequest):
    if req.selected_index not in [1, 2, 3]:
        raise HTTPException(status_code=400, detail="Invalid choice index. Must be 1, 2, or 3.")

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Fetch the selected choice
        cur.execute("SELECT * FROM pending_reward_choices WHERE player_id = %s AND choice_index = %s", (player_id, req.selected_index))
        choice = cur.fetchone()

        if not choice:
            raise HTTPException(status_code=404, detail="No pending reward found for this index.")

        # Insert base item
        cur.execute("""
            INSERT INTO items (name, sprite_path)
            VALUES (%s, %s) RETURNING id
        """, (choice["name"], choice["sprite_path"]))
        
        item_id = cur.fetchone()["id"]

        # Insert specific subtype and update player
        if choice["item_type"] == "weapon":
            cur.execute("""
                INSERT INTO weapons (item_id, damage, healing_capacity, weapon_type)
                VALUES (%s, %s, %s, %s)
            """, (item_id, choice["damage"], choice["healing_capacity"], choice["weapon_class"]))
            cur.execute("UPDATE players SET weapon_id = %s WHERE id = %s", (item_id, player_id))

        elif choice["item_type"] == "armour":
            cur.execute("""
                INSERT INTO armours (item_id, defence_amount, max_health_increase)
                VALUES (%s, %s, %s)
            """, (item_id, choice["defence_amount"], choice["max_health_increase"]))
            cur.execute("UPDATE players SET armour_id = %s WHERE id = %s", (item_id, player_id))

        elif choice["item_type"] == "accessory":
            cur.execute("""
                INSERT INTO accessories (item_id, stat_to_multiply, stat_multiplier)
                VALUES (%s, %s, %s)
            """, (item_id, choice["stat_to_multiply"], choice["stat_multiplier"]))
            # Assign to acc_slot_1 by default (could be extended later to manage inventory)
            cur.execute("UPDATE players SET acc_slot_1 = %s WHERE id = %s", (item_id, player_id))

        # Clear pending choices after successful selection
        cur.execute("DELETE FROM pending_reward_choices WHERE player_id = %s", (player_id,))

        recalculate_player_stats(player_id, cur)

        # Check if everyone else in the match is done
        cur.execute("""
            SELECT m.id, m.floor_number, m.player_1_id, m.player_2_id, m.player_3_id, m.player_4_id
            FROM matches m
            WHERE m.player_1_id = %s OR m.player_2_id = %s OR m.player_3_id = %s OR m.player_4_id = %s
        """, (player_id, player_id, player_id, player_id))
        match = cur.fetchone()

        if match:
            match_id = match["id"]
            player_ids = [pid for pid in (match["player_1_id"], match["player_2_id"], match["player_3_id"], match["player_4_id"]) if pid is not None]
            
            # Check if any player in this match still has pending choices
            cur.execute("""
                SELECT COUNT(*) as count 
                FROM pending_reward_choices 
                WHERE player_id = ANY(%s)
            """, (player_ids,))
            
            pending_count = cur.fetchone()["count"]
            
            if pending_count == 0:
                # Everyone has chosen, advance floor!
                current_floor = match.get("floor_number") or 1
                new_floor = current_floor + 1
                
                # Fetch a player name for the enemy generation
                cur.execute("SELECT player_name FROM players WHERE id = %s", (player_ids[0],))
                first_player = cur.fetchone()
                p_name = first_player["player_name"] if first_player else "Unknown"

                enemies = generate_enemies(new_floor, p_name)
                enemy_ids = []

                # Insert enemies
                for enemy in enemies:
                    cur.execute("""
                        INSERT INTO public.enemies (match_id, max_hp, current_hp, damage, armour, name)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
                    """, (match_id, enemy.max_hp, enemy.current_hp, enemy.damage, enemy.armour, enemy.name))
                    enemy_ids.append(cur.fetchone()["id"])

                # Update match
                cur.execute("""
                    UPDATE matches 
                    SET floor_number = %s, enemy_ids = %s 
                    WHERE id = %s
                """, (new_floor, enemy_ids, match_id))

        conn.commit()
        return {"status": "success", "item_type": choice["item_type"], "item_id": item_id}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/joinMatch/{player_id}")
def join_match(player_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check if player exists
        cur.execute("SELECT id FROM players WHERE id = %s", (player_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Player not found")

        # Check if player is already in an active match
        cur.execute("""
            SELECT id FROM matches 
            WHERE status IN ('waiting', 'in_progress') 
            AND %s IN (player_1_id, player_2_id, player_3_id, player_4_id)
        """, (player_id,))
        existing_match = cur.fetchone()
        
        if existing_match:
            return {"status": "already_joined", "match_id": existing_match["id"]}

        # Find an available waiting match with an open slot
        cur.execute("""
            SELECT * FROM matches 
            WHERE status = 'waiting' 
            AND (player_1_id IS NULL OR player_2_id IS NULL OR player_3_id IS NULL OR player_4_id IS NULL)
            ORDER BY id ASC LIMIT 1 FOR UPDATE
        """)
        match = cur.fetchone()

        if match:
            # Determine the first available slot
            slot_to_fill = None
            if match["player_1_id"] is None: slot_to_fill = "player_1_id"
            elif match["player_2_id"] is None: slot_to_fill = "player_2_id"
            elif match["player_3_id"] is None: slot_to_fill = "player_3_id"
            elif match["player_4_id"] is None: slot_to_fill = "player_4_id"

            # Update match with the player in the open slot
            cur.execute(f"UPDATE matches SET {slot_to_fill} = %s WHERE id = %s", (player_id, match["id"]))
            
            # If the match is now fully populated, we can mark it as in_progress
            if slot_to_fill == "player_4_id":
                cur.execute("UPDATE matches SET status = 'in_progress' WHERE id = %s", (match["id"],))

            conn.commit()
            return {"status": "success", "match_id": match["id"], "slot": slot_to_fill}
        else:
            # Create a brand new match since there are no waiting matches
            cur.execute("""
                INSERT INTO matches (status, player_1_id, floor_number) 
                VALUES ('waiting', %s, 1) RETURNING id
            """, (player_id,))
            new_match = cur.fetchone()
            
            conn.commit()
            return {"status": "success", "match_id": new_match["id"], "slot": "player_1_id"}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/startMatch/{match_id}")
def start_match(match_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Check if match exists and is waiting
        cur.execute("SELECT id, status, player_1_id FROM matches WHERE id = %s", (match_id,))
        match = cur.fetchone()

        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        if match["status"] != "waiting":
            raise HTTPException(status_code=400, detail="Match is already in progress or finished")

        # Get player 1 name for enemy generation
        cur.execute("SELECT player_name FROM players WHERE id = %s", (match["player_1_id"],))
        player = cur.fetchone()
        player_name = player["player_name"] if player else "Unknown"

        # Generate floor 1 enemies
        enemies = generate_enemies(1, player_name)
        enemy_ids = []

        # Insert enemies
        for enemy in enemies:
            cur.execute("""
                INSERT INTO public.enemies (match_id, max_hp, current_hp, damage, armour, name)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING id
            """, (match_id, enemy.max_hp, enemy.current_hp, enemy.damage, enemy.armour, enemy.name))
            enemy_ids.append(cur.fetchone()["id"])

        # Update match status to in_progress and add enemies
        cur.execute("""
            UPDATE matches 
            SET status = 'in_progress', enemy_ids = %s 
            WHERE id = %s
        """, (enemy_ids, match_id))

        conn.commit()
        return {"status": "success", "message": "Match started", "enemy_ids": enemy_ids}

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.post("/createMatch/{player_id}")
def create_match(player_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        # 1) verify player exists
        cur.execute("SELECT 1 FROM players WHERE id = %s", (player_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Player not found")

        # 2) ensure player is not already in a non-finished match
        cur.execute(
            """
            SELECT id FROM matches
            WHERE (player_1_id = %s OR player_2_id = %s OR player_3_id = %s OR player_4_id = %s)
              AND status != %s
            LIMIT 1
            """,
            (player_id, player_id, player_id, player_id, "finished"),
        )
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="Player already in an active match")

        # 3) insert new match and return id
        cur.execute(
            "INSERT INTO matches (player_1_id, status, floor_number) VALUES (%s, %s, %s) RETURNING id",
            (player_id, "waiting", 0),
        )
        match_id = cur.fetchone()["id"]
        conn.commit()

        return {"id": match_id, "status": "waiting", "floor_number": 0}

    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

@app.get("/getMatches")
def get_matches():
    # Connecting to the db
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = "SELECT * FROM matches WHERE status = 'waiting'"
        cur.execute(query)
        match = cur.fetchall()

        if not match:
            # return empty list rather than 404 so clients don't crash
            return []
            
        return match
    finally:
        cur.close()
        conn.close()

@app.get("/getMatch/{match_id}")
def get_single_match(match_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        query = "SELECT * FROM matches WHERE id = %s"
        cur.execute(query, (match_id,))
        match = cur.fetchone()

        if not match:
            raise HTTPException(status_code=404, detail="Match not found")
            
        return match
    finally:
        cur.close()
        conn.close()

# INSIDE MATCH ACTIONS

# Schema model mapping for parsing our post request body 
class AttackPayload(BaseModel):
    enemy_id: int
    damage_amount: float

@app.post("/attackEnemy/{match_id}")
def attack_enemy(match_id: int, payload: AttackPayload = Body(...)):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Fetch match to verify whose turn it is
        cur.execute("SELECT * FROM matches WHERE id = %s", (match_id,))
        match = cur.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail="Match workspace not found")

        # Reconstruct player list
        players = [match["player_1_id"], match["player_2_id"], match["player_3_id"], match["player_4_id"]]
        active_player_ids = [pid for pid in players if pid is not None]
        
        enemy_ids = match.get("enemy_ids") or []
        if enemy_ids:
            cur.execute("SELECT id FROM enemies WHERE id = ANY(%s) AND current_hp > 0 ORDER BY id ASC", (enemy_ids,))
            living_enemy_ids = [row["id"] for row in cur.fetchall()]
        else:
            living_enemy_ids = []
        
        combat_order = [("player", pid) for pid in active_player_ids] + [("enemy", eid) for eid in living_enemy_ids]
        current_turn_index = match.get("turn_index")
        if current_turn_index is None:
            current_turn_index = 0

        # 2. Safety constraint check: Is it actually a player's turn?
        if current_turn_index >= len(combat_order):
            # Reset index if boundaries mutated out of sync
            cur.execute("UPDATE matches SET turn_index = 0 WHERE id = %s", (match_id,))
            conn.commit()
            raise HTTPException(status_code=400, detail="Turn sequence desynchronized. Resetting index, please retry.")

        # 3. Check if the current attacker ID matches the client payload sender
        # Note: We assume you pass player_id from client to verify, or we derive it
        # For simplicity, we assume the action comes from whoever's turn it currently is:
        current_entity_type, current_entity_id = combat_order[current_turn_index]
        
        # If the turn index points to an enemy, a player cannot strike!
        if current_entity_type == "enemy":
            raise HTTPException(status_code=400, detail="It is currently the enemy's turn phase!")

        # 4. Process the core player attack execution 
        cur.execute("SELECT id, name, max_hp, current_hp, damage, armour FROM enemies WHERE id = %s AND match_id = %s", (payload.enemy_id, match_id))
        enemy_row = cur.fetchone()

        if not enemy_row:
            raise HTTPException(status_code=404, detail="Target enemy variant not found")

        enemy_obj = Enemy(max_hp=float(enemy_row["max_hp"]), current_hp=float(enemy_row["current_hp"]), damage=float(enemy_row["damage"]), armour=int(enemy_row["armour"]), name=str(enemy_row["name"]))
        
        if enemy_obj.current_hp <= 0:
            raise HTTPException(status_code=400, detail="Enemy is already defeated!")

        actual_damage_dealt = enemy_obj.take_damage(int(payload.damage_amount))

        cur.execute("UPDATE enemies SET current_hp = %s WHERE id = %s AND match_id = %s", (enemy_obj.current_hp, payload.enemy_id, match_id))
        
        # 5. Player strike resolved successfully! Advance the turn index.
        advance_turn_system(match_id, cur)
        
        conn.commit()
        return {
            "enemy_name": enemy_obj.name,
            "actual_damage_taken": actual_damage_dealt,
            "is_dead": (enemy_obj.current_hp <= 0),
        }

    except HTTPException as he:
        conn.rollback()
        print(f"HTTPException in attack_enemy: {he.detail}")
        raise
    except Exception as e:
        conn.rollback()
        import traceback
        traceback.print_exc()
        print(f"Exception in attack_enemy: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

# Schema model mapping for parsing our healing post request body
class HealPayload(BaseModel):
    healer_id: int
    target_player_id: int

@app.post("/healPlayer/{match_id}")
def heal_player(match_id: int, payload: HealPayload = Body(...)):
    """
    Heals a specific target player in a match using the caster's healing capacity.
    Formula: 20 + healing_capacity * 0.5
    """
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 0. Verify turn order
        cur.execute("SELECT * FROM matches WHERE id = %s", (match_id,))
        match = cur.fetchone()
        if not match:
            raise HTTPException(status_code=404, detail="Match not found")

        players = [match["player_1_id"], match["player_2_id"], match["player_3_id"], match["player_4_id"]]
        active_player_ids = [pid for pid in players if pid is not None]
        
        enemy_ids = match.get("enemy_ids") or []
        if enemy_ids:
            cur.execute("SELECT id FROM enemies WHERE id = ANY(%s) AND current_hp > 0 ORDER BY id ASC", (enemy_ids,))
            living_enemy_ids = [row["id"] for row in cur.fetchall()]
        else:
            living_enemy_ids = []
        
        combat_order = [("player", pid) for pid in active_player_ids] + [("enemy", eid) for eid in living_enemy_ids]
        current_turn_index = match.get("turn_index")
        if current_turn_index is None:
            current_turn_index = 0

        if current_turn_index >= len(combat_order):
            cur.execute("UPDATE matches SET turn_index = 0 WHERE id = %s", (match_id,))
            conn.commit()
            raise HTTPException(status_code=400, detail="Turn sequence desynchronized. Resetting index.")

        current_entity_type, current_entity_id = combat_order[current_turn_index]
        
        if current_entity_type == "enemy":
            raise HTTPException(status_code=400, detail="It is currently the enemy's turn phase!")

        # 1. Fetch the healer's profile to obtain their raw metrics
        cur.execute("SELECT * FROM players WHERE id = %s", (payload.healer_id,))
        healer_row = cur.fetchone()
        if not healer_row:
            raise HTTPException(status_code=404, detail="Healer player profile not found")

        # 2. Fetch the target's current stats
        cur.execute("SELECT * FROM players WHERE id = %s", (payload.target_player_id,))
        target_row = cur.fetchone()
        if not target_row:
            raise HTTPException(status_code=404, detail="Target player profile not found")

        # Instantiate Pydantic wrapper to evaluate modified stats safely
        healer_obj = Player(**healer_row)
        target_obj = Player(**target_row)

        # 3. Apply your custom healing calculation
        # Equation: 20 + healing_capacity * 0.5
        heal_amount = 20.0 + (healer_obj.healing_capacity * 0.5)

        # 4. Calculate new health while enforcing max health clamping
        # (Assuming your DB uses 'current_health', fallback to base health values if tracking is local)
        current_hp = target_row.get("current_health") if target_row.get("current_health") is not None else target_obj.base_max_health
        new_hp = min(current_hp + heal_amount, target_obj.max_health)

        # 5. Save the updated health value back into the target's profile
        cur.execute(
            """
            UPDATE players 
            SET current_health = %s 
            WHERE id = %s
            """,
            (new_hp, payload.target_player_id)
        )
        
        advance_turn_system(match_id, cur)
        
        conn.commit()

        return {
            "status": "success",
            "heal_calculated": heal_amount,
            "target_previous_hp": current_hp,
            "target_new_hp": new_hp,
            "max_hp_limit": target_obj.max_health
        }

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database execution error: {str(e)}")
    finally:
        cur.close()
        conn.close()

@app.get("/enemy/{enemy_id}")
def get_enemy_details(enemy_id: int):
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cur.execute("SELECT id, name, max_hp, current_hp, damage, armour FROM enemies WHERE id = %s", (enemy_id,))
        enemy = cur.fetchone()

        if not enemy:
            raise HTTPException(status_code=404, detail="Enemy variant not found")
            
        return enemy
    finally:
        cur.close()
        conn.close()