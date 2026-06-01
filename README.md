# Tesseract Language

Tesseract (o simplemente Tesseract) es un lenguaje de programación de alto nivel bajo la filosofía de **máxima flexibilidad y control**. Su principal aspiración es la unificación definitiva entre el entorno web y el escritorio (una meta que todavía se encuentra en proceso y a la que falta mucho para concretarse).

---

##  Filosofía y Visión

Tesseract está diseñado para ofrecer un control absoluto al desarrollador. El lenguaje no te impone un único estilo, sino que se adapta por completo a las necesidades de tu proyecto, permitiéndote decidir desde el tipo de sintaxis visual hasta el nivel de seguridad en el manejo de datos.

---

##  Características Principales

###  Sistema de Tipado Dual (Estático y Dinámico)
Tesseract ofrece una flexibilidad total en su sistema de tipos:
* **Tipado Dinámico:** Puedes usar variables cuyos tipos se infieren por completo en tiempo de ejecución.
* **Tipado Estático Seguro:** Puedes declarar variables de tipado seguro de forma explícita.
* **Funciones y Parámetros Flexibles:** Permite declarar funciones donde se infiere su tipo de retorno o tipar su retorno de forma estricta. Esta flexibilidad aplica exactamente igual para los parámetros que recibe la función.

```tesseract
var dinamico = "Hello";
int typed = 2;
bool isbool = true;
array arr = []; 
```
###  Control de Sintaxis: Llaves o Indentación
El lenguaje te permite elegir cómo estructurar visualmente tus bloques de código a través de parámetros de ejecución. **Nota importante:** No se pueden combinar ambos estilos dentro de un mismo archivo; debes elegir uno de los dos modos:
* Usa el parámetro `-b` para activar el **modo de llaves `{}`**.
* Usa el parámetro `-i` para activar el **modo de indentación**.

---

##  Colecciones Avanzadas

En Tesseract existen colecciones nativas como **Arrays, Tuplas y Diccionarios**. 
* **Combinación Compleja:** Puedes combinar estas colecciones entre sí para generar estructuras de datos complejas.
* **Límites y Tipado:** Tienes la capacidad de ponerles límite de tamaño y tiparlas. El tipado de una colección obliga a que todos los valores respeten ese tipo estrictamente; si anidas otra colección (como otro array, tupla o diccionario), esta igual deberá respetar el tipo definido por el contenedor padre.

```tesseract
var arr = [1,2,3];
var tupla = (4,5,6);
var dicts = {"valor1":7,"valor2":8,"valor3":9};
string[5] = ("a","b","c");  //Limitado a 5 elementos la tupla, esto aplica para arrays y dicts
float arr [0.1,0.2,0.3,[0.4,0.5]]; //una coleccion tipada solo acepta el valor float y sus colecciones anidadas
```

###  Acceso Profundo
Tesseract incorpora una renovada sintaxis diseñada específicamente para el acceso profundo a colecciones complejas y anidadas.

```tesseract
var advanced = [1,2,3,["a","b","c"],(4,5,6)];
var access = advanced[3:1]  //salida "b"
```

---

##  Sistema de Rangos Renovado

Los rangos en Tesseract operan como su propio **tipo especial** y traen capacidades expandidas:
* Soporta rangos de tipo `int`.
* Soporta rangos de tipo `float`.
* Soporta rangos de tipo `string` (estos siguen rigurosamente el orden Unicode, lo que te permite generar secuencias de símbolos y no limitarte únicamente al abecedario).

```tesseract
range r1 = 1..10; //tipo rango especial para solo esperar rangos
var r2 = "a".."z"; //orden unicode puedes poner a su vez u<unicode> a su vez para obtener los simbolos
var r2 = 0.5..1;  //rango float limitado a un decimal
```

---
##  Core Methods (Métodos Nativos)

En Tesseract, cada tipo de dato tiene métodos predefinidos integrados a los que se accede separándolos por un punto (`.`).

###  Encadenamiento e Inmutabilidad
* **Encadenamiento:** Los métodos pueden ser encadenados de forma sucesiva para realizar múltiples operaciones en una sola línea (ej. `"hola".toUpperCase().length()`).
* **Modificador de Mutabilidad (`.mut`):** Por defecto, los métodos son inmutables. Si deseas mutar la variable original directamente en el lugar (*in-place*), debes añadir el terminador `.mut` al final de la instrucción (ej. `arr.sort().mut;`).

###  Métodos de String
* **Consultas:** `length()`, `isEmpty()`, `isString()`, `charAt(index)`, `contains(val)`, `startsWith(val)`, `endsWith(val)`, `indexOf(val)`.
* **Manipulación:** `toUpperCase()`, `toLowerCase()`, `UpperFirst()`, `trim()`, `trimStart()`, `trimEnd()`, `reverse()`, `repeat(n)`, `replace(a, b)`, `split(sep)`, `slice(start, end)`.
* **Relleno:** `padStart(len, char)`, `padEnd(len, char)`.
* **Conversión y Tipado:** `typeInt()`, `typeFloat()`, `typeBool()`, `binary(n_bytes, signed)`.

###  Métodos de int y float
* **Comunes:** `abs()`, `clamp(min, max)`, `pow(exp)`, `max(val)`, `min(val)`.
* **Solo para `int`:** `isEven()`, `isOdd()`, `isPositive()`, `isNegative()`.
* **Solo para `float`:** `round(n)`, `floor()`, `ceil()`, `isNaN()`, `isInfinite()`.
* **Conversión:** `typeString()`, `typeBool()`, `typeFloat()`, `typeInt()`, `binary()`.

###  Métodos de Array
* **Mutables por defecto:** *(No requieren usar `.mut`)* `push(val)`, `pop()`, `shift()`, `unshift(val)`, `insert(index, val)`, `remove(val)`, `clear()`.
* **Inmutables por defecto:** *(Requieren encadenar `.mut` al final si deseas modificarlos en el lugar)* `sort()`, `reverse()`, `slice(start, end)`, `concat(val)`, `join(str)`, `unique()`, `flatten()`.
* **Consultas:** `length()`, `isEmpty()`, `first()`, `last()`, `contains(val)`, `indexOf(val)`.

###  Métodos de Dict
* `keys()`, `values()`, `items()`, `length()`, `isEmpty()`.

###  Métodos de Tuple
* `first()`, `last()`, `length()`, `isEmpty()`.

###  Métodos de Range
* `start()`, `end()`, `length()`, `step(n)`, `toarray()`, `totuple()`, `uni()`, `binary()`.

---
##  Estructuras de Control y Orientación a Objetos

El lenguaje viene equipado con un ecosistema completo de estructuras para controlar el flujo de la aplicación:
* **Condicionales y Selección:** `if`, `switch`.
* **Ciclos Tradicionales:** `while`, `perform-while`.
* **Manejo de Errores:** Estructura completa de `try-catch-finally`.
* **Estructuras Estilo C:** Soporte nativo para `struct`.
* **Capa de Objetos:** Toda la capa de objetos está disponible *(Nota: Esta funcionalidad es reciente y actualmente puede presentar múltiples errores)*.

###  Versatilidad en Ciclos `for`
El ciclo `for` en Tesseract es sumamente potente y cuenta con varias formas de uso para adaptarse a lo que necesites iterar:
* Iteración directa sobre Arrays, Tuplas y Diccionarios.
* Iteración sobre el sistema de Rangos.
* Iteración por condición.
* Ciclos al estilo clásico de C.
* Una variante avanzada de rango multi-variable.

```tesseract
for(var i in 1..10){...} //intera un rango  
for(var j in arr) {...} //iterar sobre un array, tupla o una coleccion
for(var z in i<10){...} //Interar sobre una condicion!
for(var a = 0; a<5;a++) {...} //estilo C
for(var x, y in i<10; arr){...} //rango multivariable itera 2 cosas a la vez el primero iterador es el que si termina acaba el ciclo
```

---
## Sistema de Librerías y Módulos

Tesseract cuenta con un sistema de librerías moderno y bien pensado, diseñado para ofrecer un aislamiento de código eficiente y una gestión de dependencias limpia.

### Importación de Librerías Nativas y Creadas
Utilizando la palabra reservada `library`, Tesseract permite importar módulos de manera precisa. Con una fuerte inspiración en Python, tienes el control total sobre qué elementos traer a tu entorno de trabajo:
* **Carga Selectiva:** Puedes cargar únicamente variables o funciones específicas separándolas por comas (`,`), evitando la sobrecarga del espacio de nombres.
* **Sistema de Aliases:** El sistema te permite asignar un alias tanto a la librería completa como a las variables y funciones individuales que decidas importar.

### Aislamiento de Archivos Fuente
Tesseract diferencia claramente las librerías del sistema de tus propios archivos fuente locales, manteniendo un aislamiento estricto por código:
* Para importar tus propios archivos de código, se utilizan comillas de forma explícita (por ejemplo, `"mycode.tss"`).
* Al igual que con las librerías, dentro de tus archivos fuente puedes extraer únicamente ciertas funciones o variables específicas y asignarles alias a las funciones, variables o a la ruta completa.

```tesseract
library math //carga la libreria nativa math
library iosettings //libreria creada con klein
library math as m //alias a la libreria
from math use pow,sqrt //solo llamas a la funcion pow y sqrt
fron math use sqrt al sq, pow //nombrastes sqrt a sq
from math use PI al pi as m
// "as" indica que nombras la libreria y al a una funcion o variable

math.pow(2,6); //si no le pusiste alias sera asi
m.pow(5,2); //si le pusiste alias
math.sq(81); //si le pusiste alias a una funcion tambien p
m.pi; //si pusiste alias a la libreria y a una variable/funcion en especifico
```
## Gestor de Paquetes: klein (En proceso)
Tesseract aspira a tener su propio gestor de paquetes oficial para la creación y publicación de módulos, el cual se encuentra actualmente en desarrollo y aún no ha sido publicado.
Este sistema se llamará **klein**, un nombre que hace referencia a la **botella de Klein** (una figura geométrica real que se puede apreciar en la cuarta dimensión espacial).

### Comandos y Parámetros Principales
El gestor de paquetes se controlará de forma sencilla a través de la terminal con parámetros clave como:
* `install`: Para instalar dependencias en tu entorno.
* `uninstall`: Para desinstalar paquetes que ya no necesites.
* `--init-lib <name>`: Para inicializar y estructurar una nueva librería desde cero.

### Arquitectura Universal y Conectividad
Aunque está pensado para ser completamente universal si solo utilizas código nativo de Tesseract, el diseño de `klein` va más allá: **permitirá linkear otros lenguajes de programación** para su uso.
Esto se traduce en una ventaja enorme, ya que te dará la flexibilidad de incorporar y aprovechar todo tipo de librerías externas sin importar su lenguaje de origen.

## Capas de Ejecución y Compilación
Tesseract trabaja sobre dos frentes principales para cumplir su meta de unificación:
1. **Capa Nativa:** Capas nativas diseñadas específicamente para compilar el código usando LLVM ir.
2. **Capa Web:** Una capa web dedicada que se encarga de transpilar el código Tesseract directamente a **JavaScript**.
