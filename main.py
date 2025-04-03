import pygame
import numpy as np
import os
import time
from collections import deque
import networkx as nx
import matplotlib.pyplot as plt

# Inicializar pygame
pygame.init()


# Clases Estado, Accion y Agente
class Estado:
    def __init__(self, fila, columna, direccion='derecha'):
        self.fila = fila
        self.columna = columna
        self.direccion = direccion

    def __eq__(self, otro):
        return self.fila == otro.fila and self.columna == otro.columna

    def __hash__(self):
        return hash((self.fila, self.columna))

    def __str__(self):
        return f"({self.fila}, {self.columna}, {self.direccion})"


class Accion:
    def __init__(self, nombre):
        self.nombre = nombre

    def __str__(self):
        return self.nombre


class Agente:
    def __init__(self, nombre, habilidades):
        self.nombre = nombre
        self.habilidades = habilidades
        self.historial = []
        self.camino_visitado = set()
        self.puntos_decision = set()

    def registrar_decision(self, estado, accion, resultado):
        self.historial.append({'estado': estado, 'accion': accion, 'resultado': resultado})
        self.camino_visitado.add((estado.fila, estado.columna))


class Problema:
    def __init__(self, estado_inicial, estados_objetivos, laberinto, agente, orden_prioridad):
        self.estado_inicial = estado_inicial
        self.estados_objetivos = estados_objetivos
        self.laberinto = laberinto
        self.agente = agente
        self.mapa_visible = np.zeros_like(laberinto)
        self.mapa_visible[estado_inicial.fila][estado_inicial.columna] = 1
        self.orden_prioridad = [self._traducir_direccion(d) for d in orden_prioridad]
        self.arbol_busqueda = nx.DiGraph()  # Árbol de búsqueda
        self.arbol_busqueda.add_node(str(estado_inicial))

    def _traducir_direccion(self, letra):
        return {'A': 'arriba', 'D': 'derecha', 'B': 'abajo', 'I': 'izquierda'}.get(letra.upper(), 'derecha')

    def es_objetivo(self, estado):
        return any(estado.fila == objetivo.fila and estado.columna == objetivo.columna
                   for objetivo in self.estados_objetivos)

    def sensar_camino(self, estado, direccion):
        fila, columna = estado.fila, estado.columna
        if direccion == "arriba":
            nueva_fila, nueva_columna = fila - 1, columna
        elif direccion == "abajo":
            nueva_fila, nueva_columna = fila + 1, columna
        elif direccion == "izquierda":
            nueva_fila, nueva_columna = fila, columna - 1
        elif direccion == "derecha":
            nueva_fila, nueva_columna = fila, columna + 1

        if 0 <= nueva_fila < len(self.laberinto) and 0 <= nueva_columna < len(self.laberinto[0]):
            self.mapa_visible[nueva_fila][nueva_columna] = 1
            return self.laberinto[nueva_fila][nueva_columna] not in [0, 5]
        return False

    def obtener_movimientos_posibles(self, estado):
        movimientos = []
        for direccion in self.orden_prioridad:
            if self.sensar_camino(estado, direccion):
                movimientos.append(direccion)
        return movimientos

    def avanzar(self, estado, direccion):
        fila, columna = estado.fila, estado.columna
        if direccion == "arriba":
            nueva_fila, nueva_columna = fila - 1, columna
        elif direccion == "abajo":
            nueva_fila, nueva_columna = fila + 1, columna
        elif direccion == "izquierda":
            nueva_fila, nueva_columna = fila, columna - 1
        elif direccion == "derecha":
            nueva_fila, nueva_columna = fila, columna + 1

        if 0 <= nueva_fila < len(self.laberinto) and 0 <= nueva_columna < len(self.laberinto[0]):
            nuevo_estado = Estado(nueva_fila, nueva_columna, direccion)
            self.arbol_busqueda.add_edge(str(estado), str(nuevo_estado), action=direccion)
            return nuevo_estado
        return None


def visualizar_laberinto_pygame(laberinto, estado_actual, problema, screen, font, cell_size=40):
    COLORES = {
        0: (0, 0, 0), 1: (255, 255, 255), 2: (0, 0, 255),
        3: (255, 255, 0), 4: (0, 128, 0), 5: (128, 128, 128),
        'oculto': (50, 50, 50), 'agente': (255, 0, 0),
        'objetivo': (0, 255, 0), 'visitado': (173, 216, 230),
        'decision': (255, 165, 0), 'camino': (220, 220, 220)
    }

    for fila in range(len(laberinto)):
        for columna in range(len(laberinto[0])):
            rect = pygame.Rect(columna * cell_size, fila * cell_size, cell_size, cell_size)
            if problema.mapa_visible[fila][columna]:
                # Celda visitada o camino
                if (fila, columna) in problema.agente.camino_visitado:
                    pygame.draw.rect(screen, COLORES['visitado'], rect)
                elif laberinto[fila][columna] in COLORES:
                    pygame.draw.rect(screen, COLORES[laberinto[fila][columna]], rect)
                else:
                    pygame.draw.rect(screen, COLORES['camino'], rect)

                # Puntos de decisión
                if (fila, columna) in problema.agente.puntos_decision:
                    pygame.draw.circle(screen, COLORES['decision'],
                                       (columna * cell_size + cell_size // 2, fila * cell_size + cell_size // 2),
                                       cell_size // 5)
            else:
                pygame.draw.rect(screen, COLORES['oculto'], rect)
            pygame.draw.rect(screen, (0, 0, 0), rect, 1)

    # Dibujar objetivo
    objetivo = problema.estados_objetivos[0]
    rect = pygame.Rect(objetivo.columna * cell_size, objetivo.fila * cell_size, cell_size, cell_size)
    pygame.draw.rect(screen, COLORES['objetivo'], rect)
    pygame.draw.rect(screen, (0, 0, 0), rect, 1)

    # Dibujar agente
    agente_rect = pygame.Rect(
        estado_actual.columna * cell_size + cell_size // 4,
        estado_actual.fila * cell_size + cell_size // 4,
        cell_size // 2,
        cell_size // 2
    )
    pygame.draw.rect(screen, COLORES['agente'], agente_rect)

    # Mostrar información
    info_text = f"Posición: ({estado_actual.fila}, {estado_actual.columna}) | Dirección: {estado_actual.direccion}"
    text_surface = font.render(info_text, True, (255, 255, 255))
    screen.blit(text_surface, (10, len(laberinto) * cell_size + 10))


def dibujar_arbol_busqueda(arbol):
    plt.figure(figsize=(15, 10))

    # Crear un diseño jerárquico por niveles
    pos = nx.drawing.nx_agraph.graphviz_layout(arbol, prog='dot', args='-Grankdir=TB')

    # Dibujar nodos y aristas con estilo
    nx.draw_networkx_nodes(
        arbol, pos,
        node_size=1500,
        node_color='#FFD700',  # Dorado
        alpha=0.9,
        linewidths=2,
        edgecolors='black'
    )

    nx.draw_networkx_edges(
        arbol, pos,
        width=2,
        alpha=0.6,
        edge_color='gray',
        arrowsize=20
    )

    # Etiquetas de nodos más claras
    nx.draw_networkx_labels(
        arbol, pos,
        font_size=8,
        font_family='sans-serif',
        font_weight='bold'
    )

    edge_labels = nx.get_edge_attributes(arbol, 'action')
    nx.draw_networkx_edge_labels(
        arbol, pos,
        edge_labels=edge_labels,
        font_size=8,
        font_color='red'
    )

    plt.title("Árbol de Búsqueda (Organizado Jerárquicamente)", fontsize=14)
    plt.axis('off')

    # Añadir cuadrícula de fondo para mejor orientación
    ax = plt.gca()
    ax.margins(0.1)
    plt.tight_layout()

    plt.show()


def busqueda_anchura(problema, screen, font, cell_size):
    cola = deque([problema.estado_inicial])
    visitados = set()
    visitados.add((problema.estado_inicial.fila, problema.estado_inicial.columna))

    while cola:
        estado_actual = cola.popleft()
        movimientos = problema.obtener_movimientos_posibles(estado_actual)

        # Registrar punto de decisión si hay múltiples movimientos
        if len(movimientos) > 1:
            problema.agente.puntos_decision.add((estado_actual.fila, estado_actual.columna))

        for direccion in movimientos:
            nuevo_estado = problema.avanzar(estado_actual, direccion)
            if nuevo_estado and (nuevo_estado.fila, nuevo_estado.columna) not in visitados:
                problema.agente.registrar_decision(estado_actual, Accion(f"avanzar_{direccion}"), nuevo_estado)
                visitados.add((nuevo_estado.fila, nuevo_estado.columna))
                cola.append(nuevo_estado)

                # Visualización
                screen.fill((0, 0, 0))
                visualizar_laberinto_pygame(problema.laberinto, nuevo_estado, problema, screen, font, cell_size)
                pygame.display.flip()
                time.sleep(0.3)

                if problema.es_objetivo(nuevo_estado):
                    return nuevo_estado
    return None


def busqueda_profundidad(problema, screen, font, cell_size):
    pila = [problema.estado_inicial]
    visitados = set()
    visitados.add((problema.estado_inicial.fila, problema.estado_inicial.columna))

    while pila:
        estado_actual = pila.pop()
        movimientos = problema.obtener_movimientos_posibles(estado_actual)

        # Registrar punto de decisión si hay múltiples movimientos
        if len(movimientos) > 1:
            problema.agente.puntos_decision.add((estado_actual.fila, estado_actual.columna))

        for direccion in reversed(movimientos):
            nuevo_estado = problema.avanzar(estado_actual, direccion)
            if nuevo_estado and (nuevo_estado.fila, nuevo_estado.columna) not in visitados:
                problema.agente.registrar_decision(estado_actual, Accion(f"avanzar_{direccion}"), nuevo_estado)
                visitados.add((nuevo_estado.fila, nuevo_estado.columna))
                pila.append(nuevo_estado)

                # Visualización
                screen.fill((0, 0, 0))
                visualizar_laberinto_pygame(problema.laberinto, nuevo_estado, problema, screen, font, cell_size)
                pygame.display.flip()
                time.sleep(0.3)

                if problema.es_objetivo(nuevo_estado):
                    return nuevo_estado
    return None


def solicitar_coordenadas(mensaje, laberinto):
    while True:
        try:
            fila = int(input(f"Ingrese fila {mensaje}: "))
            columna = int(input(f"Ingrese columna {mensaje}: "))
            if 0 <= fila < len(laberinto) and 0 <= columna < len(laberinto[0]):
                if laberinto[fila][columna] != 0:
                    return fila, columna
                print("Error: No puede ser una pared (0)")
            else:
                print("Error: Coordenadas fuera de rango")
        except ValueError:
            print("Error: Ingrese números válidos")


def main():
    # Cargar laberinto
    try:
        laberinto = np.loadtxt("map.txt", delimiter=',', dtype=int) if os.path.exists("map.txt") else np.array([
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
            [1, 0, 1, 0, 0, 0, 0, 0, 0, 1],
            [1, 0, 1, 0, 1, 1, 1, 1, 1, 1],
            [1, 0, 1, 0, 1, 0, 0, 0, 0, 1],
            [1, 0, 1, 1, 1, 1, 1, 1, 0, 1],
            [1, 0, 0, 0, 0, 0, 0, 1, 0, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 0, 1],
            [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        ])
    except Exception as e:
        print(f"Error al cargar laberinto: {e}")
        return

    # Configuración inicial
    print("\n=== Configuración del problema ===")
    print("Laberinto cargado:")
    print(laberinto)

    fila_inicio, col_inicio = solicitar_coordenadas("de inicio", laberinto)
    fila_objetivo, col_objetivo = solicitar_coordenadas("de objetivo", laberinto)

    estado_inicial = Estado(fila_inicio, col_inicio)
    estado_objetivo = Estado(fila_objetivo, col_objetivo)

    # Selección de algoritmo
    algoritmo = input("\nElija algoritmo (BFS/DFS): ").upper()
    while algoritmo not in ['BFS', 'DFS']:
        print("Error: Ingrese BFS o DFS")
        algoritmo = input("Elija algoritmo (BFS/DFS): ").upper()

    orden_prioridad = input("Orden de prioridad (ej: ADBI): ").upper()
    while not all(c in 'ADBI' for c in orden_prioridad):
        print("Error: Use solo A (Arriba), D (Derecha), B (Abajo), I (Izquierda)")
        orden_prioridad = input("Orden de prioridad (ej: ADBI): ").upper()

    # Configurar Pygame
    cell_size = 40
    width = len(laberinto[0]) * cell_size
    height = len(laberinto) * cell_size + 100
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption(f"Búsqueda {'BFS' if algoritmo == 'BFS' else 'DFS'}")
    font = pygame.font.SysFont('Arial', 20)

    # Crear problema y agente
    agente = Agente("Explorador", {'vision_lejana': True})
    problema = Problema(estado_inicial, [estado_objetivo], laberinto, agente, orden_prioridad)

    # Ejecutar búsqueda
    resultado = None
    if algoritmo == "BFS":
        resultado = busqueda_anchura(problema, screen, font, cell_size)
    else:
        resultado = busqueda_profundidad(problema, screen, font, cell_size)

    # Mostrar resultado final
    screen.fill((0, 0, 0))
    if resultado:
        mensaje = "¡Objetivo encontrado!"
        color = (0, 255, 0)
    else:
        mensaje = "No se encontró solución"
        color = (255, 0, 0)

    text_surface = font.render(mensaje, True, color)
    screen.blit(text_surface, (width // 2 - text_surface.get_width() // 2, height - 50))
    pygame.display.flip()
    time.sleep(2)

    # Mostrar árbol de búsqueda
    dibujar_arbol_busqueda(problema.arbol_busqueda)
    pygame.quit()


if __name__ == '__main__':
    main()