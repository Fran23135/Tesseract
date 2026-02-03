import sys
import os
import tempfile
import subprocess
import time
import psutil  # pip install psutil (opcional, para mediciones más detalladas)

# Importar los módulos directamente
import astAjson
import interpre

def format_time(seconds):
    """Formatea el tiempo de manera legible"""
    if seconds < 0.001:  # Menos de 1ms
        return f"{seconds * 1_000_000:.2f} μs"
    elif seconds < 1:  # Menos de 1s
        return f"{seconds * 1_000:.2f} ms"
    else:
        return f"{seconds:.6f} s"

def get_process_memory():
    """Obtiene el uso de memoria del proceso actual"""
    try:
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # MB
    except:
        return None

def main():
    if len(sys.argv) != 2:
        print("Uso: compiler_portable.exe archivo.txt")
        return
    
    source_file = sys.argv[1]
    
    # Verificar que el archivo existe
    if not os.path.exists(source_file):
        print(f"Error: El archivo {source_file} no existe")
        return
    
    # ====================================================================
    # INICIO DE MEDICIÓN TOTAL (punto de referencia absoluto)
    # ====================================================================
    inicio_absoluto = time.perf_counter()
    memoria_inicial = get_process_memory()
    
    print("=" * 70)
    print("COMPILADOR E INTÉRPRETE DEL LENGUAJE")
    print("=" * 70)
    print(f"Archivo fuente: {source_file}")
    print(f"Tamaño: {os.path.getsize(source_file)} bytes")
    print("-" * 70)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Archivos temporales
        txt_path = os.path.join(temp_dir, 'ast_output.txt')
        json_path = os.path.join(temp_dir, 'ast_output.json')
        
        # ================================================================
        # PASO 1: Parser (compiler.exe)
        # ================================================================
        print("\n[1/3] Ejecutando parser (compiler.exe)...")
        inicio_compiler = time.perf_counter()
        
        result = subprocess.run(
            ['compiler.exe', source_file, txt_path],
            capture_output=True,
            text=True
        )
        
        fin_compiler = time.perf_counter()
        tiempo_compiler = fin_compiler - inicio_compiler
        
        if result.returncode != 0:
            print("❌ Error en compiler")
            print("STDERR:", result.stderr)
            return
        
        # Verificar que se creó el archivo AST
        if not os.path.exists(txt_path):
            print("❌ El parser no generó archivo AST")
            return
            
        tamaño_ast = os.path.getsize(txt_path)
        print(f"✓ Completado en {format_time(tiempo_compiler)}")
        print(f"  AST generado: {tamaño_ast} bytes")
        
        # ================================================================
        # PASO 2: Conversión AST → JSON
        # ================================================================
        print("\n[2/3] Convirtiendo AST a JSON...")
        inicio_json = time.perf_counter()
        
        try:
            sys.argv = ['astAjson.py', txt_path, json_path]
            astAjson.main()
            fin_json = time.perf_counter()
            tiempo_json = fin_json - inicio_json
            
            if not os.path.exists(json_path):
                print("❌ No se generó el archivo JSON")
                return
                
            tamaño_json = os.path.getsize(json_path)
            print(f"✓ Completado en {format_time(tiempo_json)}")
            print(f"  JSON generado: {tamaño_json} bytes")
            
        except Exception as e:
            print(f"❌ Error en conversión JSON: {e}")
            return
        
        # ================================================================
        # PASO 3: Intérprete
        # ================================================================
        print("\n[3/3] Ejecutando intérprete...")
        print("-" * 70)
        inicio_interprete = time.perf_counter()
        
        try:
            # Desactivar modo debug del intérprete para mejor medición
            sys.argv = ['interpre.py', json_path]
            interpre.main()
            fin_interprete = time.perf_counter()
            tiempo_interprete = fin_interprete - inicio_interprete
            
        except Exception as e:
            fin_interprete = time.perf_counter()
            tiempo_interprete = fin_interprete - inicio_interprete
            print(f"\n❌ Error en intérprete: {e}")
            print(f"⏱️  Tiempo hasta error: {format_time(tiempo_interprete)}")
            return
    
    # ====================================================================
    # FIN DE MEDICIÓN TOTAL
    # ====================================================================
    fin_absoluto = time.perf_counter()
    tiempo_total = fin_absoluto - inicio_absoluto
    memoria_final = get_process_memory()
    
    # ====================================================================
    # REPORTE DETALLADO
    # ====================================================================
    print("\n" + "=" * 70)
    print("REPORTE DE RENDIMIENTO")
    print("=" * 70)
    
    # Tiempos individuales
    print("\n📊 TIEMPOS POR FASE:")
    print(f"   Parser (C/C++):     {format_time(tiempo_compiler):>15}")
    print(f"   Conversión JSON:    {format_time(tiempo_json):>15}")
    print(f"   Intérprete:         {format_time(tiempo_interprete):>15}")
    print("-" * 70)
    print(f"   TOTAL (medido):     {format_time(tiempo_total):>15}")
    
    # Porcentajes
    print("\n📈 DISTRIBUCIÓN DEL TIEMPO:")
    pct_compiler = (tiempo_compiler / tiempo_total) * 100
    pct_json = (tiempo_json / tiempo_total) * 100
    pct_interprete = (tiempo_interprete / tiempo_total) * 100
    
    print(f"   Parser:        {pct_compiler:>5.1f}%  {'█' * int(pct_compiler/2)}")
    print(f"   JSON:          {pct_json:>5.1f}%  {'█' * int(pct_json/2)}")
    print(f"   Intérprete:    {pct_interprete:>5.1f}%  {'█' * int(pct_interprete/2)}")
    
    # Overhead estimado
    overhead = tiempo_total - (tiempo_compiler + tiempo_json + tiempo_interprete)
    if overhead > 0.001:  # Si es significativo
        pct_overhead = (overhead / tiempo_total) * 100
        print(f"   Overhead:      {pct_overhead:>5.1f}%  {'█' * int(pct_overhead/2)}")
    
    # Memoria
    if memoria_inicial and memoria_final:
        uso_memoria = memoria_final - memoria_inicial
        print(f"\n💾 USO DE MEMORIA:")
        print(f"   Inicial:  {memoria_inicial:.2f} MB")
        print(f"   Final:    {memoria_final:.2f} MB")
        print(f"   Δ Usado:  {uso_memoria:+.2f} MB")
    
    # Métricas adicionales
    print(f"\n⚡ VELOCIDAD:")
    if tiempo_total > 0:
        lineas_por_seg = tamaño_ast / tiempo_total if tiempo_total > 0 else 0
        print(f"   Throughput: {lineas_por_seg:.0f} bytes/segundo")
    
    print("\n" + "=" * 70)
    
    # Análisis de cuellos de botella
    if pct_interprete > 70:
        print("\n⚠️  El intérprete es el cuello de botella principal")
        print("   Considera optimizar las operaciones más frecuentes")
    elif pct_compiler > 50:
        print("\n⚠️  El parser consume la mayor parte del tiempo")
        print("   El código C/C++ podría necesitar optimización")
    elif pct_json > 30:
        print("\n⚠️  La conversión JSON es costosa")
        print("   Considera generar JSON directamente desde el parser")

if __name__ == "__main__":
    main()