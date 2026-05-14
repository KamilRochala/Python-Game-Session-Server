import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from classes.enemy import Enemy
from classes.item import Item
from classes.weapon import Weapon, WeaponType
from classes.player import Player, PlayerClass
from classes.armour import Armour
from classes.accessory import Accessory, Stat

from main import app

# --- CLASSES ---

class TestPlayer(unittest.TestCase):

    def setUp(self):
        # Build items/accessories that satisfy Item fields
        self.weapon = Weapon(
            name="Sword",
            sprite_path="sword.png",
            damage=5,
            healing_capacity=0,
            weapon_type=WeaponType.KNIGHT,
        )
        self.armour = Armour(
            name="Plate",
            sprite_path="plate.png",
            defence_ammount=2,
            max_health_increase=10,
        )
        self.acc_dmg = Accessory(
            name="DmgRing",
            sprite_path="ring.png",
            what_stat_is_multiplied=Stat.DAMAGE,
            stat_multiplier=1.5,
        )
        self.acc_none = Accessory(
            name="Noop",
            sprite_path="noop.png",
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
            defence=0.0,
            armour=0.0,
            weapon_slot=self.weapon,
            armour_slot=self.armour,
            accessory_slot_1=self.acc_dmg,
            accessory_slot_2=self.acc_none,
            accessory_slot_3=self.acc_none,
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
                defence=0.0,
                armour=0,
                weapon_slot=self.weapon,
                armour_slot=self.armour,
                accessory_slot_1=self.acc_none,
                accessory_slot_2=self.acc_none,
                accessory_slot_3=self.acc_none,
            )

    def test_damage_with_accessory_multiplier(self):
        # damage = (base_damage + weapon.damage) * accessory_multiplier
        expected = (self.player.base_damage + self.weapon.damage) * 1.5
        self.assertAlmostEqual(self.player.damage, expected, places=6)


class TestEnemy(unittest.TestCase):

    def setUp(self):
        """Create a test enemy before each test."""
        self.enemy = Enemy(max_hp=100, current_hp=100, room_number=1, damage=20, armour=5)

    # Validator tests
    def test_valid_enemy_creation(self):
        """Test creating a valid enemy."""
        self.assertEqual(self.enemy.max_hp, 100)
        self.assertEqual(self.enemy.current_hp, 100)

    def test_max_hp_must_be_positive(self):
        """Test that max_hp validation works."""
        with self.assertRaises(ValueError):
            Enemy(max_hp=-10, current_hp=50, room_number=1, damage=20, armour=5)

    def test_current_hp_cannot_exceed_max(self):
        """Test that current_hp can't be higher than max_hp."""
        with self.assertRaises(ValueError):
            Enemy(max_hp=100, current_hp=150, room_number=1, damage=20, armour=5)

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
                damage=0,
                healing_capacity=0,
                weapon_type=WeaponType.KNIGHT,
            )

    def test_healing_capacity_only_for_cleric(self):
        with self.assertRaises(ValueError):
            Weapon(
                name="BadHeal",
                sprite_path="bad.png",
                damage=10,
                healing_capacity=5,
                weapon_type=WeaponType.KNIGHT,
            )

    def test_healing_capacity_cannot_be_negative(self):
        with self.assertRaises(ValueError):
            Weapon(
                name="NegHeal",
                sprite_path="neg.png",
                damage=10,
                healing_capacity=-1,
                weapon_type=WeaponType.CLERIC,
            )

    def test_cleric_weapon_allows_healing(self):
        wand = Weapon(
            name="Wand",
            sprite_path="wand.png",
            damage=5,
            healing_capacity=3,
            weapon_type=WeaponType.CLERIC,
        )
        self.assertEqual(wand.healing_capacity, 3)


# --- ENDPOINTS --- 

client = TestClient(app)

class TestPlayerEndpoint(unittest.TestCase):
    @patch("main.get_db_connection")
    def test_get_player_success(self, mock_get_db_connection):
        # Setup mocks
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        
        # Simulate db returning a dict for the player
        mock_cur.fetchone.return_value = {"id": 1, "player_name": "Hero1", "player_class": "knight"}
        mock_conn.cursor.return_value = mock_cur
        mock_get_db_connection.return_value = mock_conn

        # Call endpoint
        response = client.get("/player/1")

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["player_name"], "Hero1")

    @patch("main.get_db_connection")
    def test_get_player_not_found(self, mock_get_db_connection):
        mock_conn = MagicMock()
        mock_cur = MagicMock()

        mock_cur.fetchone.return_value = None
        mock_conn.cursor.return_value = mock_cur
        mock_get_db_connection.return_value = mock_conn

        response = client.get("/player/9999")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Player not found")

    @patch("main.get_db_connection")
    def test_get_reward_choices_success(self, mock_get_db_connection):
        mock_conn = MagicMock()
        mock_cur = MagicMock()

        # get_reward_choices does two initial queries: check_player_match and check_player_class
        # We simulate multiple fetchone() calls using side_effect with a list
        mock_cur.fetchone.side_effect = [
            {"id": 1, "status": "active"}, # Match row
            {"player_class": "cleric"}     # Player row
        ]
        
        mock_conn.cursor.return_value = mock_cur
        mock_get_db_connection.return_value = mock_conn

        response = client.get("/rewardChoices/1")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        
        # We expect 3 reward choices
        self.assertEqual(len(data), 3)
        self.assertIn("choice_index", data[0])
        self.assertIn("item_type", data[0])
        self.assertIn("item_data", data[0])

    @patch("main.get_db_connection")
    def test_select_reward_success(self, mock_get_db_connection):
        mock_conn = MagicMock()
        mock_cur = MagicMock()

        # select_reward requires two fetchone() calls if successful
        # 1. Fetch the pending reward choice from DB
        # 2. Get the new item_id from the INSERT ... RETURNING id query
        mock_cur.fetchone.side_effect = [
            {
                "choice_index": 1,
                "item_type": "weapon",
                "name": "Shiny Sword",
                "sprite_path": "path",
                "floor_multiplier": 1,
                "damage": 10,
                "healing_capacity": 0,
                "weapon_class": "knight"
            },
            {"id": 42} # The returned item_id
        ]
        
        mock_conn.cursor.return_value = mock_cur
        mock_get_db_connection.return_value = mock_conn

        # Call endpoint with valid index
        response = client.post("/selectReward/1", json={"selected_index": 1})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(response.json()["item_id"], 42)

    def test_select_reward_invalid_index(self):
        # We don't need to patch DB here because the index check happens before DB connection
        response = client.post("/selectReward/1", json={"selected_index": 9}) # 9 is invalid

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "Invalid choice index. Must be 1, 2, or 3.")

    @patch("main.get_db_connection")
    def test_create_match_success(self, mock_get_db_connection):
        mock_conn = MagicMock()
        mock_cur = MagicMock()

        mock_cur.fetchone.side_effect = [{"1": 1}, None, {"id": 123}]
        mock_conn.cursor.return_value = mock_cur
        mock_get_db_connection.return_value = mock_conn

        response = client.post("/createMatch/1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["match_id"], 123)

    @patch("main.get_db_connection")
    def test_create_match_conflict(self, mock_get_db_connection):
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        # 1) player exists, 2) active-match check -> returns a row (player already in match)
        mock_cur.fetchone.side_effect = [{"1": 1}, {"id": 5, "status": "waiting"}]
        mock_conn.cursor.return_value = mock_cur
        mock_get_db_connection.return_value = mock_conn

        response = client.post("/createMatch/1")
        self.assertEqual(response.status_code, 409)
        self.assertIn("already in", response.json()["detail"])

if __name__ == '__main__':
    unittest.main()