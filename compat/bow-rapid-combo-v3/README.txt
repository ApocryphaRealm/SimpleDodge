Optional override for players who run Bow Rapid Combo V3 (Archer Combat Overhaul) and want Simple Dodge's bow step
dodges instead of its back/left/right flips. Put user.json in a mod that loads after Simple Dodge, at
meshes/actors/character/animations/OpenAnimationReplacer/Simple Dodge/Bow/user.json
OAR reads it in place of Simple Dodge's own Bow config.json (it is a full copy with only the priority raised).
