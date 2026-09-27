# Graves (W8): detected the same way as Lucky Blocks and Ten Thousand
# Blocks -- family_deaths is bound to the real minecraft.custom:minecraft.deaths
# stat, compared tick-to-tick. This runs from the datapack's own tick loop,
# not the event bus, so it fires the same tick as the death -- well before
# the short respawn-screen delay -- and "at @s" still has the dead player's
# entity sitting at the death position.
#
# A stat-backed objective gives a player no score at all until that stat has
# actually incremented once -- not a score of 0, no entry whatsoever. Before
# anyone's first death, family_deaths doesn't exist for them, so copying it
# into family_deaths_prev on the line below silently does nothing, and the
# comparison two lines down ("unless A = B") is true whenever either side is
# missing -- it would fire make_grave every single tick for every player who
# has never died. Setting family_deaths_prev to a literal 0 (not a copy of
# family_deaths) fixes the init step, and gating the comparison on
# family_deaths actually existing keeps it from running before that.
execute as @a unless score @s family_deaths_prev = @s family_deaths_prev run scoreboard players set @s family_deaths_prev 0

execute as @a at @s if score @s family_deaths matches 0.. unless score @s family_deaths = @s family_deaths_prev run function family:tick/make_grave
execute as @a if score @s family_deaths matches 0.. run scoreboard players operation @s family_deaths_prev = @s family_deaths
