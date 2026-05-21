import random
import uuid

_ADJECTIVES = [
    "orange", "violet", "amber", "cobalt", "sage", "ruby", "lichen", "ivory",
    "saffron", "indigo", "moss", "cinnamon", "olive", "scarlet", "teal",
    "bronze", "crimson", "azure", "ochre", "plum",
]

_ANIMALS = [
    "walrus", "otter", "lemur", "octopus", "newt", "raven", "vole", "ibis",
    "puffin", "okapi", "marmot", "quokka", "tapir", "axolotl", "manatee",
    "wombat", "stoat", "hare", "heron", "lynx",
]


def generate_display_name(rng: random.Random | None = None) -> str:
    r = rng or random
    return f"{r.choice(_ADJECTIVES)}-{r.choice(_ANIMALS)}-{r.randint(10, 99)}"


def new_uuid() -> str:
    return str(uuid.uuid4())
