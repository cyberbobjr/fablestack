from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from back.models.domain.character import (Character, CombatStats, Equipment,
                                          Skills, Stats)
from back.models.domain.items import EquipmentItem
from back.services.equipment_service import EquipmentService


@pytest.fixture
def mock_data_service():
    mock = MagicMock()
    mock.save_character = AsyncMock()
    return mock

@pytest.fixture
def mock_equipment_manager():
    return MagicMock()

@pytest.fixture
def equipment_service(mock_data_service, mock_equipment_manager):
    return EquipmentService(mock_data_service, mock_equipment_manager)

@pytest.fixture
def mock_character():
    stats = Stats(strength=10, constitution=10, agility=10, intelligence=10, wisdom=10, charisma=10)
    skills = Skills()
    combat_stats = CombatStats(max_hit_points=50, current_hit_points=50)
    equipment = Equipment(gold=100)
    
    character = Character(user_id="123e4567-e89b-12d3-a456-426614174000", sex="male", 
        name="Test Hero",
        race="human",
        culture="gondor",
        stats=stats,
        skills=skills,
        combat_stats=combat_stats,
        equipment=equipment
    )
    return character

@pytest.mark.asyncio
async def test_decrease_item_quantity_success(equipment_service, mock_character):
    # Add an item with quantity 5
    item = EquipmentItem(
        id=str(uuid4()),
        item_id="item_arrows",  # Catalog ID
        name="Arrows (20)",
        category="consumable",
        cost_gold=0, cost_silver=2, cost_copper=0,
        weight=1.0,
        quantity=5,
        equipped=False
    )
    mock_character.equipment.consumables.append(item)
    
    # Decrease by 1
    await equipment_service.decrease_item_quantity(mock_character, "Arrows (20)", 1)
    
    assert item.quantity == 4
    assert len(mock_character.equipment.consumables) == 1
    equipment_service.data_service.save_character.assert_awaited_once()

@pytest.mark.asyncio
async def test_decrease_item_quantity_removal(equipment_service, mock_character):
    # Add an item with quantity 1
    item = EquipmentItem(
        id=str(uuid4()),
        item_id="item_potion",
        name="Potion",
        category="consumable",
        cost_gold=10, cost_silver=0, cost_copper=0,
        weight=0.5,
        quantity=1,
        equipped=False
    )
    mock_character.equipment.consumables.append(item)
    
    # Decrease by 1
    await equipment_service.decrease_item_quantity(mock_character, "Potion", 1)
    
    assert len(mock_character.equipment.consumables) == 0
    equipment_service.data_service.save_character.assert_awaited_once()

@pytest.mark.asyncio
async def test_decrease_item_quantity_multiple_removal(equipment_service, mock_character):
    # Add an item with quantity 5
    item = EquipmentItem(
        id=str(uuid4()),
        item_id="item_arrows",
        name="Arrows",
        category="consumable",
        cost_gold=0, cost_silver=0, cost_copper=0,
        weight=0.1,
        quantity=5,
        equipped=False
    )
    mock_character.equipment.consumables.append(item)
    
    # Decrease by 5
    await equipment_service.decrease_item_quantity(mock_character, "Arrows", 5)
    
    assert len(mock_character.equipment.consumables) == 0
    equipment_service.data_service.save_character.assert_awaited_once()

@pytest.mark.asyncio
async def test_decrease_item_quantity_not_found(equipment_service, mock_character):
    # Decrease non-existent item
    await equipment_service.decrease_item_quantity(mock_character, "NonExistent", 1)
    
    # Should not crash, should not save
    equipment_service.data_service.save_character.assert_not_called()

@pytest.mark.asyncio
async def test_decrease_item_quantity_case_insensitive(equipment_service, mock_character):
    # Add an item
    item = EquipmentItem(
        id=str(uuid4()),
        item_id="item_arrows",
        name="Arrows",
        category="consumable",
        cost_gold=0, cost_silver=0, cost_copper=0,
        weight=0.1,
        quantity=5,
        equipped=False
    )
    mock_character.equipment.consumables.append(item)
    
    # Decrease using lowercase
    await equipment_service.decrease_item_quantity(mock_character, "arrows", 1)
    
    assert item.quantity == 4
    equipment_service.data_service.save_character.assert_awaited_once()

@pytest.mark.asyncio
async def test_increase_item_quantity_success(equipment_service, mock_character):
    # Add an item with quantity 5
    item = EquipmentItem(
        id=str(uuid4()),
        item_id="item_arrows",
        name="Arrows (20)",
        category="consumable",
        cost_gold=0, cost_silver=2, cost_copper=0,
        weight=1.0,
        quantity=5,
        equipped=False
    )
    mock_character.equipment.consumables.append(item)
    
    # Increase by 10
    await equipment_service.increase_item_quantity(mock_character, "Arrows (20)", 10)
    
    assert item.quantity == 15
    assert len(mock_character.equipment.consumables) == 1
    equipment_service.data_service.save_character.assert_awaited_once()

@pytest.mark.asyncio
async def test_increase_item_quantity_not_found(equipment_service, mock_character):
    # Increase non-existent item
    await equipment_service.increase_item_quantity(mock_character, "NonExistent", 5)
    
    # Should not crash, should not save
    equipment_service.data_service.save_character.assert_not_called()

@pytest.mark.asyncio
async def test_increase_item_quantity_case_insensitive(equipment_service, mock_character):
    # Add an item
    item = EquipmentItem(
        id=str(uuid4()),
        item_id="item_arrows",
        name="Arrows",
        category="consumable",
        cost_gold=0, cost_silver=0, cost_copper=0,
        weight=0.1,
        quantity=5,
        equipped=False
    )
    mock_character.equipment.consumables.append(item)
    
    # Increase using different case
    await equipment_service.increase_item_quantity(mock_character, "ARROWS", 3)
    
    assert item.quantity == 8
    equipment_service.data_service.save_character.assert_awaited_once()
