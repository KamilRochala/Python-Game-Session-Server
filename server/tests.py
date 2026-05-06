import unittest

from classes.enemy import Enemy
from classes.item import Item
from classes.weapon import Weapon, WeaponType


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

if __name__ == '__main__':
    unittest.main()