# Graves (W8): detected the same way as Lucky Blocks and Ten Thousand
# Blocks -- family_deaths is bound to the real minecraft.custom:minecraft.deaths
# stat, compared tick-to-tick. This runs from the datapack's own tick loop,
# not the event bus, so it fires the same tick as the death -- well before
# the short respawn-screen delay -- and "at @s" still has the dead player's
# entity sitting at the death position.
execute as @a unless score @s family_deaths_prev = @s family_deaths_prev run scoreboard players operation @s family_deaths_prev = @s family_deaths

execute as @a at @s unless score @s family_deaths = @s family_deaths_prev run function family:tick/make_grave
execute as @a run scoreboard players operation @s family_deaths_prev = @s family_deaths
