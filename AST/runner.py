import marshal

def run_bytecode(filename):
    with open(filename, 'rb') as f:
        f.read(4)  # Leer y descartar la cabecera
        bytecode = marshal.load(f)
        exec(bytecode)

if __name__ == "__main__":
    run_bytecode('output.pyc')
