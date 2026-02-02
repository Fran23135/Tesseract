
# Sistema de guardado de nombres y apellidos
import os

def main():
    lista = []
    print("¡Sistema de guardado de nombres y apellidos!")
    
    while True:
        os.system('cls')
        print("Bienvenido")
        print("1. agregar nombre y apellido")
        print("2. consultar")
        print("3 salir")
        opc = input("Introduce una opcion:")
        if opc == "1":
         nm = input("introduce tu nombre y apellido:")
         lista.append(nm)
        elif opc == "2":  
         print(f"{lista}\n")
         c = input("Enter.....")
        elif opc == "3":
           print("Saliendo...")
           break
   

if __name__ == "__main__":
    main()
