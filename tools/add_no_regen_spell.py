"""Adds the 'No stamina regen during dodge' records to Simple Dodge.esp (1.2.0, 2026-11-12).

  0x803 MGEF SDG_NoStaminaRegenEffect - Value Modifier on StaminaRateMult (actor value 157), Detrimental + Recover,
        fire-and-forget, self; hidden in the UI, painless, no hit event or hit effect, no shader, no sounds.
        DATA starts from vanilla AlchDamageStaminaRate (Skyrim.esm 0x073F2C, also StaminaRateMult) and changes only
        the flags, the cost, the hit shader and the keyword/script/sound subrecords (dropped).
  0x804 SPEL SDG_NoStaminaRegenSpell - that effect at magnitude 100 (StaminaRateMult's base is 100, so regen is 0)
        for 3 s: the safety duration if the dodge's end event never comes. The DLL dispels it on TKDR_DodgeEnd.
        The SPIT block is the on-dodge spell's (0x802): spell, fire-and-forget, self, cost 0, manual cost.

The approach follows TK Dodge - No Stamina Regen During Dodge (Nexus 150370): a Value Modifier on StaminaRateMult.
Idempotent: a plugin that already has 0x803 is left alone.
Usage: python add_no_regen_spell.py [<Simple Dodge.esp>]
"""
import os, struct, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ESP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(HERE), "dist", "Simple Dodge.esp")
MGEF_ID, SPEL_ID = 0x02000803, 0x02000804   # master index 02 = this plugin (masters: Skyrim.esm, Update.esm)

# MGEF flags: Recover 0x2, Detrimental 0x4, NoHitEvent 0x10, HideInUI 0x8000, Painless 0x4000000, NoHitEffect 0x8000000
MGEF_FLAGS = 0x2 | 0x4 | 0x10 | 0x8000 | 0x4000000 | 0x8000000
STAMINA_RATE_MULT = 157


def sub(sig, data):
    return sig + struct.pack("<H", len(data)) + data


def record(sig, fid, body):
    return sig + struct.pack("<IIIIHH", len(body), 0, fid, 0, 44, 0) + body


def group(label, body):
    return b"GRUP" + struct.pack("<I4sIIHH", 24 + len(body), label, 0, 0, 0, 0) + body


def vanilla_data():
    """DATA of AlchDamageStaminaRate as stored in Skyrim.esm (the layout this edit is checked against)."""
    return bytes.fromhex(
        "070840009a99993e00000000ffffffffffffffff00000000000000000000000064cc1000000000000000000000000000"
        "0000003f000000000000000000000000000000009d00000000000000000000000100000000000000ffffffff00000000"
        "000000000000000000000000000000000000803f00000000000000000000000000000000000000000000000000000000"
        "0000000000000000")


def main():
    b = open(ESP, "rb").read()
    hsize = struct.unpack_from("<I", b, 4)[0]
    head, rest = b[:24 + hsize], b[24 + hsize:]
    if struct.pack("<I", MGEF_ID) in rest:
        print("already has 0x803 - unchanged")
        return
    d = bytearray(vanilla_data())
    assert len(d) == 152
    assert struct.unpack_from("<I", d, 64)[0] == 0 and struct.unpack_from("<i", d, 68)[0] == STAMINA_RATE_MULT
    struct.pack_into("<I", d, 0, MGEF_FLAGS)
    struct.pack_into("<f", d, 4, 0.0)        # base cost
    struct.pack_into("<I", d, 32, 0)         # hit shader: none
    struct.pack_into("<I", d, 80, 1)         # fire and forget
    struct.pack_into("<I", d, 84, 0)         # self
    mgef = record(b"MGEF", MGEF_ID, sub(b"EDID", b"SDG_NoStaminaRegenEffect\0") + sub(b"FULL", b"No Stamina Regen\0")
                  + sub(b"MDOB", struct.pack("<I", 0)) + sub(b"DATA", bytes(d)) + sub(b"DNAM", b"\0"))
    spit = bytes.fromhex("000000000100000000000000000000000100000000000000000000000000000000000000")
    spel = record(b"SPEL", SPEL_ID, sub(b"EDID", b"SDG_NoStaminaRegenSpell\0") + sub(b"OBND", bytes(12))
                  + sub(b"FULL", b"No Stamina Regen\0") + sub(b"ETYP", struct.pack("<I", 0x013F44)) + sub(b"DESC", b"\0")
                  + sub(b"SPIT", spit) + sub(b"EFID", struct.pack("<I", MGEF_ID))
                  + sub(b"EFIT", struct.pack("<fII", 100.0, 0, 3)))
    # split the top-level groups, add MGEF before SPEL (the engine's group order) and the spell to SPEL
    groups, i = [], 0
    while i < len(rest):
        size, label = struct.unpack_from("<I4s", rest, i + 4)
        groups.append((label, rest[i + 24:i + size]))
        i += size
    out = []
    for label, body in groups:
        if label == b"SPEL":
            out.append(group(b"MGEF", mgef))
            body = body + spel
        out.append(group(label, body))
    if not any(l == b"SPEL" for l, _ in groups):
        raise SystemExit("no SPEL group")
    # HEDR: version f32, number of records (records + groups), next object id
    hedr = head.find(b"HEDR")
    ver, count, nxt = struct.unpack_from("<fII", head, hedr + 6)
    head = bytearray(head)
    struct.pack_into("<fII", head, hedr + 6, ver, count + 3, max(nxt, 0x805))
    open(ESP, "wb").write(bytes(head) + b"".join(out))
    print("added MGEF 0x803 + SPEL 0x804; HEDR records %d -> %d, next id %X -> %X" % (count, count + 3, nxt, max(nxt, 0x805)))


if __name__ == "__main__":
    main()
