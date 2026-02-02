"""
VRP (Vehicle Routing Problem) Solver using OR-Tools
Includes HARD CONSTRAINT for Huichapan security waypoint
"""
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
from typing import List, Tuple, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class DeliveryNode:
    """Represents a delivery location or waypoint"""
    id: str
    name: str
    lat: float
    lng: float
    is_depot: bool = False
    is_security_waypoint: bool = False


@dataclass
class OptimizationResult:
    """Result of route optimization"""
    success: bool
    message: str
    ordered_nodes: List[DeliveryNode]
    total_distance_meters: int
    total_time_seconds: int
    route_sequence: List[int]


class VRPSolver:
    """
    Vehicle Routing Problem solver with security constraint.
    
    HARD CONSTRAINT: First stop after depot MUST be the security waypoint (Huichapan)
    to avoid the dangerous "Arco Norte" route.
    """
    
    def __init__(
        self,
        depot_location: Tuple[float, float],
        depot_name: str = "Almacén",
        security_waypoint: Optional[Tuple[float, float]] = None,
        security_waypoint_name: str = "Huichapan"
    ):
        self.depot = DeliveryNode(
            id="DEPOT",
            name=depot_name,
            lat=depot_location[0],
            lng=depot_location[1],
            is_depot=True
        )
        
        self.security_waypoint = None
        if security_waypoint:
            self.security_waypoint = DeliveryNode(
                id="WAYPOINT_HUICHAPAN",
                name=security_waypoint_name,
                lat=security_waypoint[0],
                lng=security_waypoint[1],
                is_security_waypoint=True
            )
    
    def solve(
        self,
        delivery_nodes: List[DeliveryNode],
        distance_matrix: List[List[int]],
        time_matrix: Optional[List[List[int]]] = None
    ) -> OptimizationResult:
        """
        Solve the VRP with security constraint.
        
        Args:
            delivery_nodes: List of delivery locations (excluding depot and waypoint)
            distance_matrix: Full distance matrix including depot [0] and optionally waypoint [1]
            time_matrix: Optional time matrix (same structure as distance_matrix)
        
        Returns:
            OptimizationResult with ordered nodes and metrics
        """
        # Build complete node list
        # Index 0: Depot
        # Index 1: Security Waypoint (if exists)
        # Index 2+: Delivery nodes
        
        all_nodes = [self.depot]
        has_waypoint = self.security_waypoint is not None
        
        if has_waypoint:
            all_nodes.append(self.security_waypoint)
        
        all_nodes.extend(delivery_nodes)
        
        num_nodes = len(all_nodes)
        
        print(f"DEBUG: VRPSolver.solve - num_nodes: {num_nodes}")
        print(f"DEBUG: VRPSolver.solve - distance_matrix size: {len(distance_matrix)}x{len(distance_matrix[0]) if distance_matrix else 0}")
        if len(distance_matrix) > 0:
            print(f"DEBUG: Matrix Row 0 sample: {distance_matrix[0]}")
            # Check types
            print(f"DEBUG: Matrix element type: {type(distance_matrix[0][0])}")
        
        if len(distance_matrix) != num_nodes:
             print(f"CRITICAL: Matrix size mismatch! Expressed {num_nodes}, got {len(distance_matrix)}")
             return OptimizationResult(False, "Error interno: Matriz de distancias incorrecta", [], 0, 0, [])
        
        if num_nodes < 2:
            return OptimizationResult(
                success=False,
                message="No hay suficientes nodos para optimizar",
                ordered_nodes=[],
                total_distance_meters=0,
                total_time_seconds=0,
                route_sequence=[]
            )
        
        # Create the routing index manager
        manager = pywrapcp.RoutingIndexManager(
            num_nodes,  # Number of locations
            1,          # Number of vehicles
            0           # Depot index
        )
        print("DEBUG: VRPSolver - RoutingIndexManager created")
        
        # Create routing model
        routing = pywrapcp.RoutingModel(manager)
        print("DEBUG: VRPSolver - RoutingModel created")
        
        # Create distance callback
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return distance_matrix[from_node][to_node]
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # Add distance dimension
        routing.AddDimension(
            transit_callback_index,
            0,          # No slack
            10000000,    # Max travel distance (10000 km) - Relaxed heavily for large routes
            True,       # Start cumul to zero
            'Distance'
        )
        
        # ========================================
        # HARD CONSTRAINT: Huichapan Security
        # ========================================
        if has_waypoint:
            # Force the vehicle to visit index 1 (Huichapan) immediately after depot
            # This is done by making Huichapan the only valid next node from depot
            # print("DEBUG: VRPSolver - Skipping Hard Constraint (Huichapan) for debugging")
            
            # Get the index for the security waypoint
            waypoint_index = manager.NodeToIndex(1)
            
            # Lock the arc from depot to waypoint
            routing.solver().Add(
                routing.NextVar(manager.NodeToIndex(0)) == waypoint_index
            )
        
        # Set search parameters
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        # ENABLE METAHEURISTIC FOR BETTER RESULTS
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.seconds = 900  # Increased to 15 mins for heavy load
        
        # Solve
        print("DEBUG: VRPSolver - Starting search...")
        solution = routing.SolveWithParameters(search_parameters)
        print("DEBUG: VRPSolver - Search completed")
        
        if not solution:
            return OptimizationResult(
                success=False,
                message="No se encontró solución óptima",
                ordered_nodes=[],
                total_distance_meters=0,
                total_time_seconds=0,
                route_sequence=[]
            )
        
        # Extract solution
        ordered_nodes = []
        route_sequence = []
        index = routing.Start(0)
        total_distance = 0
        
        while not routing.IsEnd(index):
            node_index = manager.IndexToNode(index)
            route_sequence.append(node_index)
            ordered_nodes.append(all_nodes[node_index])
            
            previous_index = index
            index = solution.Value(routing.NextVar(index))
            total_distance += routing.GetArcCostForVehicle(previous_index, index, 0)
        
        # Add final return to depot
        route_sequence.append(0)
        
        # Calculate time (assuming ~50 km/h average)
        total_time_seconds = int(total_distance / 13.89)  # 50 km/h = 13.89 m/s
        
        return OptimizationResult(
            success=True,
            message=f"Ruta optimizada con {len(ordered_nodes)} paradas",
            ordered_nodes=ordered_nodes,
            total_distance_meters=total_distance,
            total_time_seconds=total_time_seconds,
            route_sequence=route_sequence
        )


def build_distance_matrix_for_solver(
    depot: Tuple[float, float],
    security_waypoint: Optional[Tuple[float, float]],
    delivery_locations: List[Tuple[float, float]],
    api_distances: Optional[List[List[int]]] = None
) -> List[List[int]]:
    """
    Build a distance matrix in the correct order for the solver.
    
    Order: [depot, security_waypoint (if exists), ...delivery_locations]
    
    If api_distances is provided, it should already be in this order.
    Otherwise, uses haversine distances.
    """
    from app.integrations.distance_matrix import calculate_haversine_matrix
    
    locations = [depot]
    if security_waypoint:
        locations.append(security_waypoint)
    locations.extend(delivery_locations)
    
    if api_distances and len(api_distances) == len(locations):
        return api_distances
    
    return calculate_haversine_matrix(locations)
