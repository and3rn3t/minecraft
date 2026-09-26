# Called from check_lucky_blocks.mcfunction, executing as the player whose
# family_lucky_heads stat just went up. Rolls the loot table at roughly
# where they're standing -- good enough; the exact broken block's position
# isn't available from a stat change alone.
loot spawn ~ ~ ~ loot family:lucky_block
