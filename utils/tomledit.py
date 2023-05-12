import toml


def change_value(file, base, value, changeto):
    try:
        with open(file, "r") as tomlFile:
            data = toml.load(tomlFile)
    except FileNotFoundError:
        raise FileNotFoundError("The file you tried to get does not exist...")

    data[base][value] = changeto
    with open(file, "w") as tomlFile:
        toml.dump(data, tomlFile)


def append_value(file, value, addition):
    try:
        with open(file, "r") as tomlFile:
            data = toml.load(tomlFile)
    except FileNotFoundError:
        raise FileNotFoundError("The file you tried to get does not exist...")

    data[value].append(addition)
    with open(file, "w") as tomlFile:
        toml.dump(data, tomlFile)
