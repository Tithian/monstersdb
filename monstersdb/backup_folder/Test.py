def testing():
    cadena = 'Combat
Aasimars usually like a fair, straightforward contest. Against a particularly evil foe, however, they fight with utter conviction and to the death.
Daylight (Sp): An aasimar can use daylight once per day as a 1st-level caster or a caster of his class levels, whichever is higher.
Skills: An aasimar has a +2 racial bonus on Spot and Listen checks.
The aasimar warrior presented here had the following ability scores before racial adjustments: Str 13, Dex 11, Con 12, Int 10, Wis 9, Cha 8.'
    if cadena.startswith('COMBAT', 0, 6):
        new_cadena = cadena.replace('COMBAT', '', 1)
        print(new_cadena)