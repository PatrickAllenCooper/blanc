"""
Tests for orders_schema.py: Order data class and tolerant LLM response parser.

Author: Anonymous Authors
"""

import pytest
from blanc.sc2live.orders_schema import Order, parse_orders


# ---------------------------------------------------------------------------
# Order data class
# ---------------------------------------------------------------------------

class TestOrderDataClass:
    def test_attack_valid(self):
        o = Order(action="attack", unit="marine_00000041", target="enemy_00000001")
        assert o.action == "attack"
        assert o.unit == "marine_00000041"
        assert o.target == "enemy_00000001"

    def test_retreat_no_target(self):
        o = Order(action="retreat", unit="zealot")
        assert o.target is None

    def test_hold_no_target(self):
        o = Order(action="hold", unit="marine")
        assert o.action == "hold"

    def test_action_normalised_lowercase(self):
        o = Order(action="ATTACK", unit="marine", target="enemy")
        assert o.action == "attack"

    def test_attack_without_target_raises(self):
        with pytest.raises(ValueError, match="target"):
            Order(action="attack", unit="marine")

    def test_unknown_action_raises(self):
        with pytest.raises(ValueError, match="Unknown action"):
            Order(action="nuke", unit="marine", target="enemy")

    def test_to_dict(self):
        o = Order(action="attack", unit="m", target="e")
        d = o.to_dict()
        assert d == {"action": "attack", "unit": "m", "target": "e"}


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

class TestParseOrdersJSON:
    def test_plain_json_array(self):
        text = '[{"action":"attack","unit":"marine","target":"enemy"}]'
        orders = parse_orders(text)
        assert len(orders) == 1
        assert orders[0].action == "attack"
        assert orders[0].unit == "marine"
        assert orders[0].target == "enemy"

    def test_json_with_retreat_no_target(self):
        text = '[{"action":"retreat","unit":"zealot"}]'
        orders = parse_orders(text)
        assert len(orders) == 1
        assert orders[0].action == "retreat"
        assert orders[0].target is None

    def test_json_multiple_orders(self):
        text = '[{"action":"attack","unit":"m1","target":"e1"},{"action":"hold","unit":"m2"}]'
        orders = parse_orders(text)
        assert len(orders) == 2

    def test_json_with_orders_key(self):
        text = '{"orders":[{"action":"attack","unit":"m","target":"e"}]}'
        orders = parse_orders(text)
        assert len(orders) == 1

    def test_single_json_object(self):
        text = '{"action":"hold","unit":"marine"}'
        orders = parse_orders(text)
        assert len(orders) == 1
        assert orders[0].action == "hold"

    def test_fenced_json(self):
        text = '```json\n[{"action":"attack","unit":"m","target":"e"}]\n```'
        orders = parse_orders(text)
        assert len(orders) == 1

    def test_fenced_without_lang(self):
        text = '```\n[{"action":"retreat","unit":"m"}]\n```'
        orders = parse_orders(text)
        assert len(orders) == 1

    def test_json_with_prose_preamble(self):
        text = 'Here are my orders:\n[{"action":"attack","unit":"m","target":"e"}]'
        orders = parse_orders(text)
        assert len(orders) == 1

    def test_empty_json_array(self):
        orders = parse_orders("[]")
        assert orders == []

    def test_invalid_action_in_json_skipped(self):
        text = '[{"action":"nuke","unit":"m","target":"e"},{"action":"hold","unit":"m2"}]'
        orders = parse_orders(text)
        # nuke is invalid and should be skipped; hold should succeed
        assert len(orders) == 1
        assert orders[0].action == "hold"


# ---------------------------------------------------------------------------
# Prose / bullet-list parsing
# ---------------------------------------------------------------------------

class TestParseOrdersProse:
    def test_simple_attack_line(self):
        text = "attack marine enemy"
        orders = parse_orders(text)
        assert len(orders) == 1
        assert orders[0].action == "attack"

    def test_engage_synonym(self):
        text = "engage marine_1 enemy_probe"
        orders = parse_orders(text)
        assert len(orders) == 1
        assert orders[0].action == "attack"

    def test_retreat_synonym_withdraw(self):
        text = "withdraw zealot"
        orders = parse_orders(text)
        assert len(orders) == 1
        assert orders[0].action == "retreat"

    def test_hold_synonym(self):
        text = "hold position marine"
        orders = parse_orders(text)
        assert len(orders) == 1
        assert orders[0].action == "hold"

    def test_bullet_list(self):
        text = "- attack marine enemy\n- retreat zealot"
        orders = parse_orders(text)
        assert len(orders) == 2

    def test_numbered_list(self):
        text = "1. attack marine enemy\n2. hold marine2"
        orders = parse_orders(text)
        assert len(orders) == 2

    def test_empty_string(self):
        orders = parse_orders("")
        assert orders == []

    def test_no_orders_in_prose(self):
        orders = parse_orders("The weather is nice today.")
        assert orders == []
