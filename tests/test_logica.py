import pytest
import random
from unittest.mock import patch

# Importación de funciones de lógica pura y utilidades matemáticas
from funcionesAuxiliaresPartida import (
    tirarDados, 
    obtener_puntuacion, 
    ordenar_por_cercania, 
    deshacer_empates
)

# Importación de controladores de resolución de minijuegos
from logicaMinijuegos import (
    resolver_minijuego,
    finalizar_minijuego_casilla,
    finalizar_minijuego_orden
)

# ==============================================================================
# OBJETOS MOCK (SIMULADORES DE ENTORNO)
# ==============================================================================

class DummySession:
    """
    Mock de la clase GameSession.
    Se utiliza para aislar la lógica de los minijuegos de la capa de red (WebSockets)
    y de la base de datos. Almacena el estado de la partida en memoria para 
    permitir la validación mediante aserciones (asserts) durante los tests.
    """
    def __init__(self):
        # Variables de estado del minijuego
        self.minijuego_tipo = None
        self.minijuego_actual = None
        self.minijuego_scores = {}
        self.minijuego_participantes = []
        self.minijuego_detalles = {}
        
        # Estado simulado del tablero y los jugadores
        self.board_state = {
            "order": {},
            "balances": {"Edu1": 10, "Edu2": 10, "Edu3": 10, "Edu4": 10}
        }
        
        # Registro de llamadas de red simuladas
        self.broadcast_llamado_con = None

    async def broadcast(self, message: dict):
        """
        Simula el envío de un mensaje WebSocket a todos los clientes.
        Almacena el payload del mensaje para su posterior validación en los tests.
        """
        self.broadcast_llamado_con = message


# ==============================================================================
# TESTS DE FUNCIONES AUXILIARES (Lógica matemática y estructuras de datos)
# ==============================================================================

@pytest.mark.parametrize("posicion, max_dado2", [
    (1, 6), # El jugador en 1ª posición tira un d6 adicional
    (2, 4), # El jugador en 2ª posición tira un d4 adicional
    (3, 2), # El jugador en 3ª posición tira un d2 (moneda) adicional
    (4, 0)  # El jugador en 4ª posición no obtiene dado adicional
])
def test_tirarDados_validacion_limites(posicion, max_dado2):
    """
    Verifica que la función tirarDados genera valores dentro de los límites
    esperados para cada una de las posiciones posibles del turno.
    """
    d1, d2, suma = tirarDados(posicion)
    
    # Validación del dado principal (siempre d6)
    assert 1 <= d1 <= 6
    
    # Validación del dado secundario según la ventaja por posición
    if max_dado2 > 0:
        assert 1 <= d2 <= max_dado2
    else:
        assert d2 == 0
        
    # Validación de la integridad del resultado
    assert suma == d1 + d2

def test_obtener_puntuacion_tupla():
    """
    Verifica la correcta extracción del valor numérico desde una 
    tupla de formato (id_jugador, puntuacion).
    """
    assert obtener_puntuacion(("JugadorX", 450)) == 450

def test_ordenar_por_cercania_absoluta():
    """
    Verifica que el algoritmo de ordenación por cercanía calcula correctamente
    la diferencia absoluta respecto a un objetivo y ordena la lista de forma
    ascendente según dicha diferencia.
    """
    scores = {"P1": 20, "P2": 55, "P3": 50, "P4": 100}
    # Diferencias esperadas respecto a 50: P1(30), P2(5), P3(0), P4(50)
    # Orden de menor a mayor diferencia: P3, P2, P1, P4
    
    resultado = ordenar_por_cercania(scores.items(), objetivo=50)
    
    assert resultado[0][0] == "P3"
    assert resultado[1][0] == "P2"
    assert resultado[2][0] == "P1"
    assert resultado[3][0] == "P4"

def test_deshacer_empates_aleatoriedad():
    """
    Verifica que el algoritmo agrupa correctamente las puntuaciones idénticas
    y aplica aleatoriedad (shuffle) únicamente dentro de los grupos empatados,
    respetando el orden global del ranking.
    """
    ranking_con_empate = [("P1", 100), ("P2", 100), ("P3", 50)]
    
    # Se ejecuta iterativamente para cubrir variaciones probabilísticas del shuffle
    for _ in range(5):
        resultado = deshacer_empates(ranking_con_empate)
        
        # El jugador con menor puntuación debe permanecer invariablemente último
        assert resultado[2][0] == "P3"
        
        # Los jugadores empatados deben ocupar las dos primeras posiciones
        nombres_top2 = [resultado[0][0], resultado[1][0]]
        assert "P1" in nombres_top2
        assert "P2" in nombres_top2


# ==============================================================================
# TESTS DE LÓGICA DE MINIJUEGOS (Operaciones Asíncronas)
# ==============================================================================

@pytest.mark.asyncio
async def test_resolver_minijuego_limpieza_estado():
    """
    Verifica que el gestor central de minijuegos purga correctamente las 
    variables de estado temporal de la sesión tras finalizar la resolución.
    """
    session = DummySession()
    session.minijuego_tipo = "orden"
    session.minijuego_actual = "Reflejos"
    session.minijuego_scores = {"A": 1, "B": 2}
    
    await resolver_minijuego(session)
    
    assert session.minijuego_actual is None
    assert session.minijuego_tipo is None
    assert session.minijuego_scores == {}
    assert session.minijuego_participantes == []

@pytest.mark.asyncio
async def test_finalizar_minijuego_orden_menor_tiempo():
    """
    Verifica la asignación de turnos basada en el menor tiempo (ascendente).
    Aplicable a minijuegos como 'Reflejos'.
    """
    session = DummySession()
    session.minijuego_actual = "Reflejos"
    session.minijuego_scores = {"Edu1": 500, "Edu2": 250, "Edu3": 300, "Edu4": 800}
    
    await finalizar_minijuego_orden(session)
    
    # Validación de las posiciones asignadas en el estado global (1º a 4º)
    assert session.board_state["order"]["Edu2"] == 1
    assert session.board_state["order"]["Edu3"] == 2
    assert session.board_state["order"]["Edu1"] == 3
    assert session.board_state["order"]["Edu4"] == 4

@pytest.mark.asyncio
async def test_finalizar_minijuego_orden_mayor_valor():
    """
    Verifica la asignación de turnos basada en el mayor valor (descendente).
    Aplicable a minijuegos como 'Mayor o Menor'.
    """
    session = DummySession()
    session.minijuego_actual = "Mayor o Menor"
    session.minijuego_scores = {"Edu1": 5, "Edu2": 12, "Edu3": 3, "Edu4": 7}
    
    await finalizar_minijuego_orden(session)
    
    assert session.board_state["order"]["Edu2"] == 1
    assert session.board_state["order"]["Edu4"] == 2
    assert session.board_state["order"]["Edu1"] == 3
    assert session.board_state["order"]["Edu3"] == 4


# --- PRUEBAS DE MINIJUEGOS DE CASILLA (Matriz de pagos / Teoría de Juegos) ---

@pytest.mark.parametrize("decision_p1, decision_p2, delta_p1, delta_p2", [
    ("cooperar", "cooperar", 2, 2),     # Cooperación mutua (recompensa media)
    ("traicionar", "traicionar", 0, 0), # Traición mutua (sin recompensa)
    ("traicionar", "cooperar", 3, 0),   # P1 traiciona, P2 coopera (P1 maximiza)
    ("cooperar", "traicionar", 0, 3),   # P1 coopera, P2 traiciona (P2 maximiza)
])
@pytest.mark.asyncio
async def test_finalizar_minijuego_dilema_prisionero_matriz_pagos(decision_p1, decision_p2, delta_p1, delta_p2):
    """
    Verifica la correcta resolución de la matriz de pagos del 'Dilema del Prisionero'.
    Evalúa las cuatro combinaciones posibles de decisiones y su impacto en el saldo.
    """
    session = DummySession()
    session.minijuego_actual = "Dilema del Prisionero"
    session.minijuego_participantes = ["Edu1", "Edu2"]
    session.minijuego_scores = {"Edu1": decision_p1, "Edu2": decision_p2}
    
    saldo_inicial_1 = session.board_state["balances"]["Edu1"]
    saldo_inicial_2 = session.board_state["balances"]["Edu2"]
    
    await finalizar_minijuego_casilla(session)
    
    # Validación de la actualización de saldos según la matriz de pagos
    assert session.board_state["balances"]["Edu1"] == saldo_inicial_1 + delta_p1
    assert session.board_state["balances"]["Edu2"] == saldo_inicial_2 + delta_p2
    
    # Validación del broadcast de actualización económica
    assert session.broadcast_llamado_con is not None
    assert session.broadcast_llamado_con["type"] == "balances_changed"


# --- PRUEBAS DE MINIJUEGOS DE AZAR (Inyección de dependencias mediante Patch) ---

@pytest.mark.asyncio
@patch("random.random") 
async def test_finalizar_minijuego_doble_o_nada_victoria(mock_random):
    """
    Verifica la correcta duplicación de la apuesta en caso de victoria.
    Utiliza mock patching sobre random.random() para garantizar determinismo
    en la prueba, forzando un escenario de éxito (valor < 0.5 o > 0.5 según lógica).
    """
    # Se fuerza la devolución de un valor específico para asegurar la rama de victoria
    mock_random.return_value = 0.9 
    
    session = DummySession()
    session.minijuego_actual = "Doble o Nada"
    session.minijuego_participantes = ["Edu1"]
    session.minijuego_scores = {"Edu1": 5} # Representa la cantidad apostada
    
    saldo_inicial = session.board_state["balances"]["Edu1"]
    
    await finalizar_minijuego_casilla(session) 
    
    # En caso de victoria, se suma la apuesta al saldo original
    assert session.board_state["balances"]["Edu1"] == saldo_inicial + 5