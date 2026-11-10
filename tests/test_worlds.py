import pytest

from agency_garden.errors import ConfigurationError
from agency_garden.worlds import Commons, Trust


@pytest.mark.parametrize("multiplier", [1, 2, 3])
@pytest.mark.parametrize("contributions", [(0, 0, 0), (1, 2, 4), (10, 10, 10)])
def test_commons_credit_arithmetic(multiplier, contributions):
    world = Commons(rounds=1, multiplier=multiplier)
    actors = ("a", "b", "c")
    state = world.initial(actors, 17)
    new = world.advance(
        state, {a: {"contribute": n} for a, n in zip(actors, contributions, strict=True)}
    )
    assert sum(new["credits"].values()) == 30 + sum(contributions) * (multiplier - 1)
    assert state["round"] == 0
    assert world.finished(new)
    assert world.active(new) == ()
    assert world.outcomes(new)["total_credits"] == sum(new["credits"].values())


def test_private_needs_and_equal_seed():
    world = Commons()
    state = world.initial(("a", "b"), 4)
    assert state == world.initial(("a", "b"), 4)
    view = world.observe(state, "a")
    assert view["your_need"] == state["needs"]["a"]
    assert "needs" not in view
    assert "your_need" not in world.observe(state, "b")["history"]


def test_integer_remainders_rotate():
    world = Commons(rounds=3, multiplier=1)
    state = world.initial(("a", "b", "c"), 0)
    for _ in range(3):
        state = world.advance(
            state, {"a": {"contribute": 1}, "b": {"contribute": 0}, "c": {"contribute": 0}}
        )
    assert state["credits"] == {"a": 28, "b": 31, "c": 31}


@pytest.mark.parametrize("sent,returned", [(0, 0), (1, 3), (5, 6), (10, 30)])
def test_trust_transfers_and_roles(sent, returned):
    world = Trust(rounds=2)
    state = world.initial(("a", "b"), 0)
    assert world.active(state) == ("a",)
    state = world.advance(state, {"a": {"send": sent}})
    assert world.active(state) == ("b",)
    assert world.observe(state, "b")["received"] == 3 * sent
    state = world.advance(state, {"b": {"return": returned}})
    assert state["credits"] == {"a": 10 - sent + returned, "b": 10 + 3 * sent - returned}
    assert world.active(state) == ("b",)
    assert world.outcomes(state)["total_returned"] == returned


@pytest.mark.parametrize("world,actors", [(Commons(), ("a",)), (Trust(), ("a", "b", "c"))])
def test_world_participant_counts(world, actors):
    with pytest.raises(ConfigurationError):
        world.initial(actors, 0)


@pytest.mark.parametrize(
    "parameters",
    [{"rounds": 0}, {"multiplier": True}, {"need_min": 12, "need_max": 1}, {"typo": 2}],
)
def test_world_parameters_are_strict(parameters):
    with pytest.raises(ValueError):
        Commons(**parameters)
