# Runs last in main.mcfunction's tick, after check_deaths (and everything
# it calls, including the grave vacuum) has already run this same tick.
#
# Tags every item entity currently in the world as "seen". An item that
# just dropped from a death this tick hasn't been tagged yet -- that's
# exactly the window vacuum_grave_step.mcfunction uses to tell "the dead
# player's own drops" apart from items that were already lying around
# nearby (someone else's deliberate drop, an older unrelated pile) without
# needing to track ownership by distance. Untagged survives exactly one
# tick: anything not swept into a grave gets tagged here and is excluded
# from every future death's vacuum.
tag @e[type=item] add family_seen_item
