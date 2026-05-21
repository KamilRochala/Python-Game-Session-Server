import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Import models and classes from your app
from main import app, SelectionRequest, AttackPayload, HealPayload
from classes.enemy import Enemy
from classes.item import Item
from classes.weapon import Weapon, WeaponType
from classes.player import Player, PlayerClass
from classes.armour import Armour
from classes.accessory import Accessory, Stat


# Initialize the test client for FastAPI
client = TestClient(app)

# ---------------------------------------------------------
# PYDANTIC AND DOMAIN CLASS TESTS
# ---------------------------------------------------------

class TestPlayer(unittest.TestCase):

    def setUp(self):
        # Build items/accessories that satisfy Item fields
        self.weapon = Weapon(
            name="Sword",
            sprite_path="sword.png",
            floor_multiplier=1,
            damage=5,
            healing_capacity=0,
            weapon_type=WeaponType.KNIGHT,
        )
        self.armour = Armour(
            name="Plate",
            sprite_path="plate.png",
            floor_multiplier=1,
            defence_ammount=2,
            max_health_increase=10,
        )
        self.acc_dmg = Accessory(
            name="DmgRing",
            sprite_path="ring.png",
            floor_multiplier=1,
            what_stat_is_multiplied=Stat.DAMAGE,
            stat_multiplier=1.5,
        )
        self.acc_none = Accessory(
            name="Noop",
            sprite_path="noop.png",
            floor_multiplier=1,
            what_stat_is_multiplied=Stat.DEFENCE,
            stat_multiplier=1.0,
        )

        self.player = Player(
            player_name="Hero1",
            player_class=PlayerClass.KNIGHT,
            base_max_health=100.0,
            max_health=100.0,
            current_health=100.0,
            base_damage=10.0,
            damage=10.0,
            base_healing_capacity=0.0,
            healing_capacity=0.0,
            base_defence=0.0,
            armour=0.0,
            weapon_slot=self.weapon,
            armour_slot=self.armour,
            accessory_slot_1=self.acc_dmg,
        )

    def test_valid_player_creation(self):
        self.assertEqual(self.player.player_name, "Hero1")
        self.assertEqual(self.player.player_class, PlayerClass.KNIGHT)

    def test_name_must_be_alphanumeric(self):
        with self.assertRaises(ValueError):
            Player(
                player_name="bad name!",
                player_class=PlayerClass.KNIGHT,
                base_max_health=50,
                max_health=50,
                current_health=50,
                base_damage=5,
                damage=5,
                base_healing_capacity=0,
                healing_capacity=0,
                base_defence=0.0,
                armour=0,
                weapon_slot=self.weapon,
                armour_slot=self.armour,
                accessory_slot_1=self.acc_none,
            )

    def test_damage_with_accessory_multiplier(self):
        # damage = (base_damage + weapon.damage) * accessory_multiplier
        expected = (self.player.base_damage + self.weapon.damage) * 1.5
        self.assertAlmostEqual(self.player.damage, expected, places=6)


class TestEnemy(unittest.TestCase):

    def setUp(self):
        """Create a test enemy before each test."""
        self.enemy = Enemy(max_hp=100, current_hp=100, name="Orc", damage=20, armour=5)

    # Validator tests
    def test_valid_enemy_creation(self):
        """Test creating a valid enemy."""
        self.assertEqual(self.enemy.max_hp, 100)
        self.assertEqual(self.enemy.current_hp, 100)

    def test_max_hp_must_be_positive(self):
        """Test that max_hp validation works."""
        with self.assertRaises(ValueError):
            Enemy(max_hp=-10, current_hp=50, name="Orc", damage=20, armour=5)

    def test_current_hp_cannot_exceed_max(self):
        """Test that current_hp can't be higher than max_hp."""
        with self.assertRaises(ValueError):
            Enemy(max_hp=100, current_hp=150, name="Orc", damage=20, armour=5)

    # Method tests
    def test_take_damage(self):
        """Test damage calculation with armour."""
        actual_damage = self.enemy.take_damage(30)
        self.assertEqual(actual_damage, 25)  # 30 - 5 armour
        self.assertEqual(self.enemy.current_hp, 75)  # 100 - 25
    
    def test_take_damage_armor_absorption(self):
        """Test that armour reduces damage properly."""
        self.enemy.take_damage(7)  # 7 - 5 armour = 2 damage
        self.assertEqual(self.enemy.current_hp, 98)
    
    def test_hp_cannot_go_below_zero(self):
        """Test that HP doesn't go negative."""
        self.enemy.take_damage(1000)
        self.assertGreaterEqual(self.enemy.current_hp, 0)
    
    def test_deal_damage_when_alive(self):
        """Test that alive enemy deals damage."""
        damage = self.enemy.deal_damage()
        self.assertIn(damage, range(18, 23))  # 20 ± 2
    
    def test_deal_damage_when_dead(self):
        """Test that dead enemy deals 0 damage."""
        self.enemy.current_hp = 0
        self.assertEqual(self.enemy.deal_damage(), 0)

class TestWeapon(unittest.TestCase):

    def setUp(self):
        """Create a test weapon before each test."""
        self.weapon = Weapon(
            name="Sword",
            sprite_path="sword.png",
            floor_multiplier=1,
            damage=10,
            healing_capacity=0,
            weapon_type=WeaponType.KNIGHT,
        )

    # Validator tests
    def test_valid_weapon_creation(self):
        self.assertEqual(self.weapon.damage, 10)
        self.assertEqual(self.weapon.healing_capacity, 0)
        self.assertEqual(self.weapon.weapon_type, WeaponType.KNIGHT)

    def test_damage_must_be_positive(self):
        with self.assertRaises(ValueError):
            Weapon(
                name="Bad",
                sprite_path="bad.png",
                floor_multiplier=1,
                damage=0,
                healing_capacity=0,
                weapon_type=WeaponType.KNIGHT,
            )

    def test_healing_capacity_only_for_cleric(self):
        with self.assertRaises(ValueError):
            Weapon(
                name="BadHeal",
                sprite_path="bad.png",
                floor_multiplier=1,
                damage=10,
                healing_capacity=5,
                weapon_type=WeaponType.KNIGHT,
            )

    def test_healing_capacity_cannot_be_negative(self):
        with self.assertRaises(ValueError):
            Weapon(
                name="NegHeal",
                sprite_path="neg.png",
                floor_multiplier=1,
                damage=10,
                healing_capacity=-1,
                weapon_type=WeaponType.CLERIC,
            )

    def test_cleric_weapon_allows_healing(self):
        wand = Weapon(
            name="Wand",
            sprite_path="wand.png",
            floor_multiplier=1,
            damage=5,
            healing_capacity=3,
            weapon_type=WeaponType.CLERIC,
        )
        self.assertEqual(wand.healing_capacity, 3)

class TestArmour(unittest.TestCase):

    def setUp(self):
        self.armour = Armour(
            name="Iron Chest",
            sprite_path="iron_chest.png",
            floor_multiplier=1,
            defence_ammount=5,
            max_health_increase=20
        )

    def test_valid_armour_creation(self):
        self.assertEqual(self.armour.defence_ammount, 5)
        self.assertEqual(self.armour.max_health_increase, 20)

    def test_defence_must_be_non_negative(self):
        with self.assertRaises(ValueError):
            Armour(
                name="Bad Armour",
                sprite_path="bad.png",
                floor_multiplier=1,
                defence_ammount=-5,
                max_health_increase=10
            )

class TestAccessory(unittest.TestCase):

    def test_valid_accessory_creation(self):
        acc = Accessory(
            name="Ring of Power",
            sprite_path="ring.png",
            floor_multiplier=1,
            what_stat_is_multiplied=Stat.DAMAGE,
            stat_multiplier=1.2
        )
        self.assertEqual(acc.stat_multiplier, 1.2)
        self.assertEqual(acc.what_stat_is_multiplied, Stat.DAMAGE)


class TestPayloadModels(unittest.TestCase):

    def test_selection_request(self):
        req = SelectionRequest(selected_index=2)
        self.assertEqual(req.selected_index, 2)
        # Assuming you want valid indices to be tested later in endpoints or added as validators in model

    def test_attack_payload(self):
        payload = AttackPayload(enemy_id=1, damage_amount=15.5)
        self.assertEqual(payload.enemy_id, 1)
        self.assertEqual(payload.damage_amount, 15.5)

    def test_heal_payload(self):
        payload = HealPayload(healer_id=1, target_player_id=2)
        self.assertEqual(payload.healer_id, 1)
        self.assertEqual(payload.target_player_id, 2)


# ---------------------------------------------------------
# FASTAPI ENDPOINT MOCK TESTS
# ---------------------------------------------------------

class TestEndpoints(unittest.TestCase):

    @patch('main.get_db_connection')
    def test_get_player_success(self, mock_db):
        # 1. Setup fake database response
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "id": 1, 
            "player_name": "Hero", 
            "player_class": "Knight",
            "current_health": 100
        }
        # Wire up the mock connection -> cursor
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        # 2. Make the request to our FastAPI app
        response = client.get("/player/1")

        # 3. Assert the outcome
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["player_name"], "Hero")
        self.assertEqual(response.json()["current_health"], 100)

    @patch('main.get_db_connection')
    def test_get_player_not_found(self, mock_db):
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None # Database returns nothing
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        response = client.get("/player/999")
        
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Player not found")

    @patch('main.get_db_connection')
    def test_create_match_success(self, mock_db):
        mock_cursor = MagicMock()
        # First call checks if player exists. Let's say yes.
        # Second call checks if player is in active match. Let's say no (returns None)
        # Third call creates match and returns id.
        mock_cursor.fetchone.side_effect = [
            {"1": 1},  # Player exists
            None,      # Player not in an active match
            {"id": 42} # Return new match id
        ]
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        response = client.post("/createMatch/1")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 42)
        self.assertEqual(response.json()["status"], "waiting")
        
    @patch('main.get_db_connection')
    def test_get_matches(self, mock_db):
        mock_cursor = MagicMock()
        # Return a list of waiting matches
        mock_cursor.fetchall.return_value = [
            {"id": 1, "status": "waiting", "player_1_id": 1},
            {"id": 2, "status": "waiting", "player_1_id": 2}
        ]
        
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        response = client.get("/getMatches")
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)
        self.assertEqual(response.json()[0]["id"], 1)

    @patch('main.get_db_connection')
    def test_attack_enemy_success(self, mock_db):
        # We need to mock several DB queries to bypass the turn system & enemy checks.
        mock_cursor = MagicMock()
        
        # Side effects for fetchone in order of execution in attackEnemy endpoint:
        mock_cursor.fetchone.side_effect = [
            # 1. get match data
            {"id": 1, "turn_index": 0, "player_1_id": 1, "player_2_id": None, "player_3_id": None, "player_4_id": None, "enemy_ids": [100]},
            # 2. get enemy data
            {"id": 100, "name": "Slime", "max_hp": 50, "current_hp": 50, "damage": 5, "armour": 2},
            # ... subsequent fetchones inside advance_turn_system ...
            {"id": 1, "turn_index": 1, "player_1_id": 1, "player_2_id": None, "player_3_id": None, "player_4_id": None, "enemy_ids": [100]}
        ]
        
        # Mock fetchall for the active players/enemies check inside get_combat_order
        mock_cursor.fetchall.side_effect = [
            [{"id": 1}],     # Active players
            [{"id": 100}],   # Living enemies
            [{"id": 1}],     # Active players (for advance_turn_system)
            [{"id": 100}]    # Living enemies (for advance_turn_system)
        ]

        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db.return_value = mock_conn

        # Payload to attack enemy 100 for 12 damage
        payload = {"enemy_id": 100, "damage_amount": 12.0}
        response = client.post("/attackEnemy/1", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["enemy_name"], "Slime")
        self.assertEqual(data["is_dead"], False)
        # Enemy has 2 armour, we hit for 12, damage taken should be 10.
        self.assertEqual(data["actual_damage_taken"], 10)


if __name__ == '__main__':
    unittest.main()