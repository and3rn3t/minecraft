# Called from check_deaths.mcfunction, executing as the player who just
# died, at their death position.
#
# Two players can die at the same spot, or an earlier grave there might not
# have expired yet -- placing straight onto "~ ~ ~" would silently overwrite
# an existing grave's chest (and whatever's still boxed inside it) rather
# than making a new one, and family:tick/age_graves has no way to tell two
# graves apart if they end up sharing one chest. Step 2 blocks east until an
# empty spot is found. Two people on a home server essentially never stack
# three graves on the exact same block, so three tries is enough without an
# unbounded search -- a fourth death on top of the first three reuses the
# third slot, a documented edge case rather than a silent one.
execute unless block ~ ~ ~ minecraft:chest run function family:tick/place_grave
execute if block ~ ~ ~ minecraft:chest unless block ~2 ~ ~ minecraft:chest positioned ~2 ~ ~ run function family:tick/place_grave
execute if block ~ ~ ~ minecraft:chest if block ~2 ~ ~ minecraft:chest positioned ~4 ~ ~ run function family:tick/place_grave
