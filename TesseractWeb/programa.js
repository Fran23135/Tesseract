// ============================================================
// Generado por runtimeweb.js — Tesseract WebIR Transpiler
// tess_web_ir: 1.0
// ============================================================

// -- Helper lectura --
function __tessRead(prompt) {
  return window.prompt(String(prompt) || "") || "";
}

// -- Programa --
let op /*string*/ = "";
let numero = parseInt(op, 10);
let n /*number*/ = 1;
let ing /*Array*/ = ["Dog", "Apple", "Ship", "Computer", "Mouse", "People", "Cat", "Sport", "City", "Tree", "Window", "Console", "Storage", "Docs", "Disk", "Minute", "One", "Home", "Themes", "Hit"];
let esp /*Array*/ = ["Perro", "Manzana", "Barco", "Computadora", "Raton", "Persona", "Gato", "Deporte", "Ciudad", "Arbol", "Ventana", "Consola", "Capacida", "Documen tos", "Disco", "Minuto", "Uno", "Casa", "Temas", "Golpear"];
let pIng = null;
do {
  console.log("1.Traducir ingles a español");
  console.log("2.Traducir de español a ingles");
  console.log("3.Salir");
  console.log("ingresa la opcion:");
  op = __tessRead("");
  numero = parseInt(op, 10);
  switch (numero) {
    case 1: {
      console.log("  Elegiste Traducir ingles a español ");
      console.log("ingresa la palabra:");
      pIng = __tessRead("");
      let com = ing.includes(pIng);
      if (ing.includes(pIng)) {
        let index = ing.indexOf(pIng);
        let pal = esp[index];
        console.log("Traduccion: " + String(pal));
      } else {
        console.log("Palabra no encontrada");
      }
      console.log("    Pulsa Enter para Continuar");
      op = __tessRead("");
      break;
    }
    case 2: {
      console.log("  Elegiste Traducir ingles a español ");
      console.log("ingresa la palabra:");
      let pEsp = null;
      pEsp = __tessRead("");
      let com = ing.includes(pIng);
      if (com) {
        let index = esp.indexOf(pEsp);
        let pal1 = ing[index];
        console.log("Traduccion: " + String(pal1));
      } else {
        console.log("Palabra no encontrada");
      }
      console.log("Pulsa Enter para Continuar");
      op = __tessRead("");
      break;
    }
    case 3: {
      console.log("Saliendo...");
      break;
    }
    default: {
      console.log("opcion no existente");
      break;
    }
  }
} while ((numero != 3));