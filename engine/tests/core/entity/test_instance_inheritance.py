import pytest
from pydantic import Field

from tangl.core import InheritingSingleton

class TestInheritingSingleton:
    """Test suite for InheritingSingleton behavior"""

    class Character(InheritingSingleton):
        """Test class for inheritance scenarios"""
        name: str
        level: int = 1
        hp: int = 100
        mp: int = 50
        traits: set[str] = Field(default_factory=set)

    @pytest.fixture(autouse=True)
    def reset_char_class(self):
        self.Character.clear_instances()

    def test_basic_inheritance(self):
        """Test basic inheritance of default values"""
        # Create base character
        warrior = self.Character(
            label="warrior",
            name="Generic Warrior",
            hp=150,
            traits={"strong", "brave"}
        )

        # Create inheriting character
        elite = self.Character(
            label="elite",
            from_ref="warrior",
            name="Elite Warrior"  # Override just the name
        )

        # Verify inherited values
        assert elite.hp == 150  # Inherited
        assert elite.mp == 50  # Default value
        assert elite.level == 1  # Default value
        assert elite.traits == {"strong", "brave"}  # Inherited set
        assert elite.name == "Elite Warrior"  # Overridden

        # Verify they're different instances
        assert elite.uid != warrior.uid
        assert elite.label != warrior.label

    def test_chained_inheritance(self):
        """Test inheritance can be chained through multiple levels"""
        base = self.Character(
            label="base",
            name="Base",
            hp=100
        )

        improved = self.Character(
            label="improved",
            from_ref="base",
            hp=150,
            traits={"tough"}
        )

        elite = self.Character(
            label="elite",
            from_ref="improved",
            name="Elite",
            traits={"tough", "skilled"}
        )

        assert elite.hp == 150  # From improved
        assert elite.traits == {"tough", "skilled"}  # Merged
        assert elite.name == "Elite"  # Overridden
        assert elite.mp == 50  # Original default

    def test_inheritance_with_missing_ref(self):
        """Test proper error handling for missing reference"""
        with pytest.raises(KeyError):
            self.Character(
                label="invalid",
                from_ref="nonexistent",
                name="Invalid"
            )

    def test_circular_inheritance_prevention(self):
        """Test that circular inheritance is prevented"""
        base = self.Character(
            label="base",
            name="Base"
        )

        # Try to create a circular reference
        with pytest.raises(ValueError, match=r".*circular.*"):
            self.Character(
                label="circular",
                from_ref="base",
                name="Circular"
            )._instances["base"].from_ref = "circular"

    def test_complex_data_inheritance(self):
        """Test inheritance of more complex data structures"""

        class ComplexCharacter(InheritingSingleton):
            name: str
            stats: dict[str, int] = Field(default_factory=dict)
            buffs: list[str] = Field(default_factory=list)

        base = ComplexCharacter(
            label="base",
            name="Base",
            stats={"str": 10, "dex": 8},
            buffs=["haste"]
        )

        derived = ComplexCharacter(
            label="derived",
            from_ref="base",
            stats={"str": 12}  # Partial override
        )

        # Verify complex data structure inheritance
        assert derived.stats == {"str": 12, "dex": 8}  # Should only have overridden value
        assert derived.buffs == ["haste"]  # Should inherit list
        assert derived.name == "Base"  # Should inherit name

    def test_partial_updates(self):
        """Test that partial updates work correctly with inheritance"""
        base = self.Character(
            label="base",
            name="Base",
            hp=100,
            traits={"tough"}
        )

        # Create with minimal overrides
        partial = self.Character(
            label="partial",
            from_ref="base",
            traits={"tough", "quick"}  # Only override traits
        )

        assert partial.name == "Base"  # Inherited
        assert partial.hp == 100  # Inherited
        assert partial.traits == {"tough", "quick"}  # Merged
        assert partial.mp == 50  # Default
