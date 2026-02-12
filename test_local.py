"""Script para probar la API localmente."""
import requests
import json

# URL base de la API
BASE_URL = "http://localhost:8000"

# Datos de prueba
test_data = {
    "codigo_proyecto": "MY-000-2026",
    "myma": {
        "especialistas": [
            {"id": 192, "nombre": "Alan Flores"},
            {"id": 193, "nombre": "Angel Galaz"}
        ],
        "conductores": [
            {"id": 81, "nombre": "Pedrito"}
        ],
        "vehiculos": []
    },
    "externo": {
        "empresa": "AGQ",
        "especialistas": [
            {"id": 194, "nombre": "Daniel Rodriguez"},
            {"id": 195, "nombre": "Jaime Sepulveda"}
        ],
        "conductores": [
            {"id": 82, "nombre": "Diego"},
            {"id": 83, "nombre": "Joaquin"}
        ],
        "vehiculos": []
    }
}


def test_health():
    """Test del endpoint de health."""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")


def test_root():
    """Test del endpoint raíz."""
    print("Testing / endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")


def test_crear_carpetas():
    """Test del endpoint crear carpetas."""
    print("Testing /carpetas/crear endpoint...")
    print(f"Request data: {json.dumps(test_data, indent=2)}\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/carpetas/crear",
            json=test_data,
            timeout=300  # 5 minutos timeout
        )
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Éxito!")
            print(f"Código proyecto: {result.get('codigo_proyecto')}")
            print(f"Año: {result.get('año_proyecto')}")
            print(f"Drive ID: {result.get('drive_id')}")
            print(f"\nJSON Final (primeros 500 caracteres):")
            print(json.dumps(result.get('json_final', {}), indent=2)[:500])
        else:
            print(f"❌ Error: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error de conexión: {e}")
        print("Asegúrate de que el servidor esté ejecutándose en http://localhost:8000")


if __name__ == "__main__":
    print("=" * 80)
    print("PRUEBAS LOCALES DE LA API")
    print("=" * 80)
    print()
    
    test_health()
    test_root()
    
    print("¿Deseas probar el endpoint crear_carpetas? (puede tardar varios minutos)")
    print("Presiona Enter para continuar o Ctrl+C para cancelar...")
    try:
        input()
        test_crear_carpetas()
    except KeyboardInterrupt:
        print("\nPruebas canceladas.")

